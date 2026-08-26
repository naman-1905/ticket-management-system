# FastAPI Implementation Plan — Ticket Management System Backend

> Companion document to [`system_plan.md`](./system_plan.md). This plan covers **only** the FastAPI application under `backend/` (plus the local dev services it needs in Docker Compose). Jenkins CI/CD and Kubernetes deployment from system_plan.md are explicitly out of scope here.

## 1. Scope

| In scope | Out of scope |
|---|---|
| FastAPI app: API, ORM models, services, background workers | Jenkins pipeline |
| PostgreSQL schema + SQLAlchemy 2.x (async) layer | Kubernetes manifests / Helm |
| Redis usage (idempotency keys, event dedup, caching) | Frontend / UI |
| RabbitMQ event publishing & consuming | Production secret-management tooling |
| Local dev stack in `compose.yaml` (Postgres, Redis, RabbitMQ) | MongoDB integration (deferred — see §11) |
| Multi-stage Dockerfile for the API image | Load-testing infrastructure (optional locust script only) |

## 2. Current state vs target

| Component | Today | Target |
|---|---|---|
| `backend/app/main.py` | Sync app, `/`, `/health`, `/health/db` | App factory + lifespan (workers), middleware (request-id, CORS, metrics), router registration per module |
| `backend/app/db/database.py` | **Sync** engine (`create_engine`) | Async engine (`create_async_engine`) + session factory + `get_db` dependency; `/health/db` updated to async check |
| `requirements.txt` | fastapi, uvicorn, sqlalchemy, psycopg[binary] | + pydantic-settings, argon2-cffi, PyJWT, redis, aio-pika, structlog, prometheus-fastapi-instrumentator (dev: pytest, pytest-asyncio, httpx, coverage) |
| `Dockerfile` | Single-stage, root user | Multi-stage build, non-root user, healthcheck |
| `compose.yaml` | API service only | + `postgres`, `redis`, `rabbitmq` services with healthchecks; API depends on them |
| `.env.example` | `POSTGRES_*` only | Full settings reference (JWT, Redis, RabbitMQ, CORS, logging — see §10) |

## 3. Locked technology choices

| Concern | Choice | Rationale |
|---|---|---|
| Async DB driver | **psycopg v3 async engine** (`postgresql+psycopg` + `create_async_engine`) | Already in requirements; avoids adding asyncpg and its Python 3.14 wheel-availability risk; SQLAlchemy 2.x fully supports it |
| Settings | `pydantic-settings` (`BaseSettings`) | Env-driven config, typed validation at startup (system_plan Phase 0) |
| Password hashing | `argon2-cffi` | Actively maintained; passlib is unmaintained and problematic on Python 3.14 |
| JWT | `PyJWT` | Lightweight, maintained; access + refresh tokens with distinct `type` claims |
| Redis client | `redis.asyncio` (from `redis`) | Native async; used for idempotency keys + event dedup |
| RabbitMQ client | `aio-pika` | Async-native, plays well with FastAPI lifespan tasks |
| Structured logging | `structlog` (JSON renderer) | Clean JSON logs with correlation fields (system_plan Phase 0) |
| Metrics | `prometheus-fastapi-instrumentator` | Drop-in `/metrics` + request histograms; custom counters per module |
| Testing | `pytest` + `pytest-asyncio` + `httpx.AsyncClient` (ASGITransport) | Async end-to-end against the real app; test Postgres from compose |

## 4. Target project structure

```
backend/
├── Dockerfile                     # multi-stage, non-root
├── requirements.txt               # runtime deps
├── requirements-dev.txt           # pytest, pytest-asyncio, httpx, coverage
└── app/
    ├── main.py                    # create_app(), lifespan (workers), middleware, routers
    ├── core/
    │   ├── config.py              # Settings(BaseSettings) — all env vars typed here
    │   ├── security.py            # argon2 hash/verify, JWT encode/decode, get_current_user, require_roles()
    │   ├── logging.py             # structlog JSON setup + RequestIdMiddleware (request_id, duration_ms)
    │   └── errors.py              # AppError hierarchy → exception handlers → error envelope (§5.2)
    ├── db/
    │   ├── database.py            # async engine, session factory, get_db() dependency
    │   └── base.py                # Declarative Base + constraint naming conventions
    └── modules/                   # bounded contexts; each has models/schemas/services/routes
        ├── identity/              # models.py schemas.py services.py repositories.py routes.py
        ├── ticketing/             # models.py schemas.py services.py repositories.py state_machine.py events.py routes.py
        ├── sla/                   # models.py schemas.py services.py worker.py routes.py
        ├── notifications/         # models.py schemas.py services.py consumer.py routes.py
        └── audit/                 # models.py schemas.py service.py routes.py   (leaf module)
```

**Module dependency rule (no cycles):** `audit` depends on nothing. `identity` is standalone. `ticketing` → `identity` (FK), `ticketing` → `sla` + `notifications` via **events only** (RabbitMQ / in-process queue). `sla` and `notifications` read ticket data through their own repositories, never by importing ticketing internals.

## 5. Cross-cutting conventions

### 5.1 Request/response envelope
- Success: return the resource directly (no wrapper) — standard FastAPI style.
- Errors: single JSON shape from exception handlers in `core/errors.py`:
```json
{ "error": { "code": "TICKET_STATE_INVALID", "message": "...", "details": {} } }
```
- Error codes are stable strings (e.g. `AUTH_REQUIRED`, `FORBIDDEN`, `NOT_FOUND`, `VALIDATION_ERROR`, `IDEMPOTENCY_MISMATCH`, `CONFLICT`). HTTP status maps to the code; clients may branch on either.

### 5.2 Pagination & filtering
- Query params: `page` (1-based, default 1), `size` (default 20, max 100).
- Response shape for list endpoints: `{ "items": [...], "total": n, "page": p, "size": s }`.
- Filtering via query params per endpoint (e.g. `/tickets?status=OPEN&priority=P1&assignee_id=...`); sorting via `sort=-created_at` style param where needed.

### 5.3 Idempotency (system_plan §4.2)
- Client sends `Idempotency-Key: <uuid>` on mutating endpoints (`POST /tickets`, ticket state transitions, comment creation).
- Server stores the key in Redis with a **fingerprint** of the request body; first call executes and caches the response; replay returns the cached response; same key + different fingerprint → `409 IDEMPOTENCY_MISMATCH`. TTL 24h.

### 5.4 Correlation & logging
- `RequestIdMiddleware` reads incoming `X-Request-ID` (or generates a UUID), sets it on `structlog.contextvars`, echoes it in the response header, and logs `request_id`, method, path, status, `duration_ms`.
- Every event published/consumed carries `correlation_id` (= request id of the originating action) so an audit trail can be reconstructed across services.

### 5.5 Background workers (system_plan §4.3)
- Started as asyncio tasks in FastAPI **lifespan** (`async with lifespan(app)`), each with a supervisor loop that restarts on exception and shuts down cleanly on SIGTERM/SIGINT.
- Workers: `sla_worker` (deadline scan, 60s interval), `notification_consumer` (RabbitMQ queue).
- Dev fallback: if RabbitMQ is unreachable at startup, workers log a warning and run in **in-process mode** (events dispatched via an asyncio queue) so the API remains fully usable locally.

### 5.6 Security rules
- Passwords hashed with Argon2id; never logged or returned after creation.
- JWT access tokens: 15 min TTL, `type=access`; refresh tokens: 7 days, `type=refresh`, stored hashed in DB (rotation on use).
- Role checks via a reusable `require_roles("ADMIN", "AGENT")` dependency; role hierarchy enforced server-side (`ADMIN > AGENT > CUSTOMER`).
- Passwords and JWT secrets are never included in logs or error responses.

## 6. Data model (SQLAlchemy 2.x, async)

All tables: `id UUID PK default gen_random_uuid()`, `created_at`/`updated_at TIMESTAMPTZ`. Constraint names follow the convention `{table}_{columns}_{type}` for stable Alembic migrations later.

### 6.1 identity
| Table | Columns (beyond id/timestamps) | Notes |
|---|---|---|
| `users` | `email CITEXT UNIQUE NOT NULL`, `full_name VARCHAR(200)`, `password_hash TEXT NOT NULL`, `role VARCHAR(20) CHECK IN ('ADMIN','AGENT','CUSTOMER') DEFAULT 'CUSTOMER'`, `is_active BOOLEAN DEFAULT true` | Argon2 hash; email unique index for login lookup |
| `refresh_tokens` | `user_id FK→users ON DELETE CASCADE`, `token_hash TEXT UNIQUE NOT NULL`, `expires_at TIMESTAMPTZ NOT NULL`, `revoked_at TIMESTAMPTZ NULL`, `created_by_ip INET NULL` | Rotation: revoke on use; hash-only storage |

### 6.2 ticketing
| Table | Columns | Notes |
|---|---|---|
| `tickets` | `ticket_number VARCHAR(20) UNIQUE NOT NULL` (e.g. `TCK-2026-000123`), `title VARCHAR(300)`, `description TEXT`, `status VARCHAR(20) DEFAULT 'OPEN' CHECK IN ('OPEN','IN_PROGRESS','ON_HOLD','RESOLVED','CLOSED')`, `priority VARCHAR(5) DEFAULT 'P3' CHECK IN ('P1','P2','P3','P4')`, `category VARCHAR(50) NULL`, `customer_id FK→users NOT NULL`, `assignee_id FK→users NULL`, `created_by FK→users NOT NULL` | Indexes on `(status, priority)` and `assignee_id` for queue views |
| `comments` | `ticket_id FK→tickets ON DELETE CASCADE`, `author_id FK→users NOT NULL`, `body TEXT NOT NULL`, `is_internal BOOLEAN DEFAULT false` | Internal notes hidden from CUSTOMER role at query time |

### 6.3 sla
| Table | Columns | Notes |
|---|---|---|
| `sla_policies` | `name VARCHAR(100) UNIQUE`, `priority VARCHAR(5) NOT NULL`, `first_response_minutes INT NOT NULL`, `resolution_hours INT NOT NULL`, `is_active BOOLEAN DEFAULT true` | Seed defaults: P1 30m/4h, P2 2h/8h, P3 8h/24h, P4 24h/72h |
| `ticket_sla` | `ticket_id FK→tickets UNIQUE NOT NULL`, `policy_id FK→sla_policies NOT NULL`, `first_response_due_at TIMESTAMPTZ`, `resolution_due_at TIMESTAMPTZ`, `first_responded_at TIMESTAMPTZ NULL`, `resolved_at TIMESTAMPTZ NULL`, `status VARCHAR(20) DEFAULT 'ACTIVE' CHECK IN ('ACTIVE','MET','BREACHED')` | One row per ticket; worker maintains due dates and status transitions |

### 6.4 notifications
| Table | Columns | Notes |
|---|---|---|
| `notification_templates` | `key VARCHAR(50) UNIQUE NOT NULL`, `channel VARCHAR(20) DEFAULT 'EMAIL'`, `subject_template TEXT`, `body_template TEXT` | Seed: `ticket.created`, `ticket.assigned`, `comment.added`, `sla.breached` |
| `notifications` | `recipient_id FK→users NOT NULL`, `ticket_id FK→tickets NULL`, `template_key VARCHAR(50) NOT NULL`, `channel VARCHAR(20) DEFAULT 'EMAIL'`, `subject TEXT`, `body TEXT`, `status VARCHAR(20) DEFAULT 'PENDING' CHECK IN ('PENDING','SENT','FAILED')`, `sent_at TIMESTAMPTZ NULL` | In production the "email" channel is a stub service that logs + marks SENT (no SMTP in scope); table keeps the audit trail |

### 6.5 audit
| Table | Columns | Notes |
|---|---|---|
| `audit_logs` | `actor_id FK→users NULL`, `action VARCHAR(100) NOT NULL` (e.g. `ticket.created`, `ticket.status_changed`), `entity_type VARCHAR(50) NOT NULL`, `entity_id UUID NULL`, `old_values JSONB NULL`, `new_values JSONB NULL`, `ip_address INET NULL`, `correlation_id UUID NULL` | Append-only; no UPDATE/DELETE paths in code; index on `(entity_type, entity_id)` and `created_at` |

### 6.6 State machine (ticketing/state_machine.py)
```
OPEN ──▶ IN_PROGRESS ──▶ RESOLVED ──▶ CLOSED
 │           │  ▲            │
 │           ▼  │            ▼
 └──────── ON_HOLD ◀────── (reopen: RESOLVED → OPEN, allowed for AGENT/ADMIN only)
```
- Allowed transitions enforced in one place (`state_machine.py`); invalid transition → `409 TICKET_STATE_INVALID`.
- Every transition writes an audit log row and publishes a ticket event.

## 7. API design (all under `/api/v1`)

### 7.1 Auth — `auth.py`
| Method | Path | Roles | Description |
|---|---|---|---|
| POST | `/auth/register` | public | Create CUSTOMER account; returns user + access token |
| POST | `/auth/login` | public | Email/password → `{access_token, refresh_token}` (rate-limited: 5/min/IP) |
| POST | `/auth/refresh` | public | Rotate refresh token → new pair |
| GET | `/auth/me` | any authenticated | Current user profile |

### 7.2 Tickets — `tickets.py`
| Method | Path | Roles | Description |
|---|---|---|---|
| POST | `/tickets` | CUSTOMER+ | Create ticket (idempotent); auto-assigns SLA policy by priority; publishes `ticket.created` |
| GET | `/tickets` | role-scoped | List with filters: `status`, `priority`, `category`, `customer_id`, `assignee_id`; CUSTOMER sees only own, AGENT/ADMIN see all (or filtered) |
| GET | `/tickets/{id}` | owner or staff | Ticket detail incl. SLA info; 403 for other customers |
| PATCH | `/tickets/{id}/status` | role-scoped | Body `{ "status": "IN_PROGRESS" }`; state-machine validated; publishes `ticket.status_changed` |
| POST | `/tickets/{id}/assign` | AGENT/ADMIN | Body `{ "assignee_id": ... }`; publishes `ticket.assigned` |
| GET | `/tickets/{id}/comments` | owner or staff | Comments (internal ones only for staff) |
| POST | `/tickets/{id}/comments` | owner or staff | Body `{ "body", "is_internal" }`; idempotent; publishes `comment.added` |

### 7.3 SLA — `sla.py`
| Method | Path | Roles | Description |
|---|---|---|---|
| GET | `/sla/policies` | AGENT/ADMIN | List policies |
| POST | `/sla/policies` | ADMIN | Create policy |
| PATCH | `/sla/policies/{id}` | ADMIN | Update (only for inactive or future-dated use) |
| GET | `/tickets/{id}/sla` | owner or staff | Due dates, remaining time, status |

### 7.4 Users — `users.py`
| Method | Path | Roles | Description |
|---|---|---|---|
| GET | `/users` | ADMIN/AGENT | List users (filter by role) |
| PATCH | `/users/{id}/role` | ADMIN | Change role (cannot demote self if last admin — guard in service) |

### 7.5 Audit — `audit.py`
| Method | Path | Roles | Description |
|---|---|---|---|
| GET | `/audit/logs` | ADMIN | Filter by `entity_type`, `entity_id`, `actor_id`, date range; paginated |

### 7.6 Health & meta — `health.py`
- `GET /healthz` → `{ "status": "ok", "db": "up|down" }` (liveness + DB ping, no auth).
- `GET /api/v1/meta/version` → app version + git sha (useful for correlation with logs).

### 7.7 Event catalog (published by ticketing/sla workers)
| Event | Producer | Payload highlights | Consumers |
|---|---|---|---|
| `ticket.created` | tickets service | ticket_id, customer_id, priority, created_at | sla_worker (start timers), notifications |
| `ticket.status_changed` | tickets service | ticket_id, old_status, new_status, actor_id | sla_worker (first_response/resolved timestamps), notifications |
| `ticket.assigned` | tickets service | ticket_id, assignee_id, actor_id | notifications |
| `comment.added` | comments service | ticket_id, author_id, is_internal | notifications (skip internal) |
| `sla.breached` | sla_worker | ticket_id, policy_name, breached_at | notifications, audit |

## 8. Testing strategy (pytest + httpx AsyncClient)

### 8.1 Fixtures (`tests/conftest.py`)
- **DB**: per-test transactional rollback — one `AsyncSession`, commit at end of test rolled back; keeps suite fast and isolated.
- **Event bus**: in-memory fake implementing the same interface (records published events, can be awaited) so tests assert on side effects deterministically.
- **Auth helpers**: factory users for each role + pre-built Bearer headers (`customer_headers`, `agent_headers`, `admin_headers`).
- **Clock**: inject a fake clock into SLA services (no real sleeps in tests).

### 8.2 Unit tests (pure logic, no I/O)
| Area | Key cases |
|---|---|
| State machine | every legal transition accepted; every illegal pair rejected with `409`; reopen rules; closed is terminal except reopen-by-owner |
| SLA math | first-response/resolution due dates per priority; business-hours vs 24×7 policies; breach detection at boundary (exactly-at-due = not breached); paused tickets don't accrue time |
| RBAC matrix | each endpoint × each role → expected 200/403/401 |
| Idempotency | same `Idempotency-Key` twice → one row, second call returns stored response; different key → new row |

### 8.3 API integration tests (httpx against app with test DB)
- **Auth**: register/login/refresh happy path; wrong password 401; expired access token 401 + refresh works; login rate limit 429 after threshold.
- **Tickets lifecycle**: customer creates → agent assigns → in progress → resolved → closed; each step asserts audit row + published event; customer cannot see another customer's ticket (403); customer cannot set status to RESOLVED (403).
- **Comments**: internal comments invisible to customers; idempotent comment creation.
- **SLA endpoints**: policy CRUD admin-only; `/tickets/{id}/sla` returns correct remaining time with fake clock.
- **Audit**: filter + pagination correctness.

### 8.4 Worker tests (async, fake bus + fake clock)
- `ticket.created` → SLA timers created for the right policy.
- `ticket.status_changed` to IN_PROGRESS by agent → first_response_at set once only.
- Clock advanced past due date on open ticket → `sla.breached` published exactly once (idempotent breach).
- Poison message: malformed event logged + dropped, worker keeps running.

### 8.5 Running the suite
```bash
pytest -q                 # full suite
pytest tests/unit         # fast loop while editing logic
pytest --cov=app          # coverage gate ≥ 90% on app/services/ and app/workers/
```
CI runs the full suite plus `ruff check` and `mypy app`.

## 9. Implementation order (milestones)

Each milestone ends with a green test suite; build strictly in this order so every layer has something to lean on.

| # | Milestone | Deliverables | Exit criteria |
|---|---|---|---|
| M1 | Skeleton & infra | Project scaffold, `config.py`, logging, DB engine/session, Alembic init + first migration (users), `/healthz` | App boots; migration applies to a clean Postgres; health check green |
| M2 | Auth | User model complete, JWT service, auth endpoints, RBAC dependencies, rate limiting on login | All auth integration tests pass; wrong-role access returns 403 everywhere |
| M3 | Tickets core | Ticket/Comment models + migrations, state machine module, ticket CRUD + status + assign endpoints, audit logging wired in | Full lifecycle test passes with audit rows and events asserted |
| M4 | Idempotency & hardening | `idempotency_keys` table, middleware, error handler polish (consistent 4xx bodies), pagination on list endpoints | Duplicate POST returns stored response; no endpoint leaks stack traces |
| M5 | SLA domain | Policy model + CRUD, SLA timer service with injectable clock, `/tickets/{id}/sla`, breach detection logic | Unit tests for due-date math and boundary breaches pass |
| M6 | Event bus & workers | Bus interface + in-memory impl (dev) / Redis impl (prod), publisher wiring in services, `sla_worker` consuming events, graceful shutdown | Worker tests pass; killing worker mid-message loses nothing (at-least-once verified manually) |
| M7 | Observability & polish | Request-ID middleware, structured logs with correlation IDs, `/meta/version`, OpenAPI docs review, README runbook | Trace a request end-to-end via log IDs; docs accurate against code |

Suggested timebox: M1–M2 in one day each, M3–M4 two days each, M5–M7 one to two days each. Total ≈ 10–12 focused working days for one developer.

## 10. Risks & mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| SLA business-hours math is fiddly (timezones, holidays) | Wrong breach notifications erode trust | Keep clock + calendar injectable; start with a simple "24×7" and "business hours 9–5 local" policy set; table-driven unit tests for every boundary case; defer holiday calendars to v2 behind the same interface |
| Event delivery gaps (worker down during publish) | Missed SLA timers / audit drift | At-least-once semantics + idempotent handlers (breach flag is a DB column, not an event); periodic reconciliation job in `sla_worker` that re-scans open tickets whose due date has passed but no breach row exists |
| N+1 queries on ticket list with comments/SLA joins | Slow API under load | Eager-load only what the response needs; add composite indexes `(customer_id, status)`, `(assignee_id, status)` in M3 migration; verify with `EXPLAIN` during M7 |
| JWT secret / config mismanagement in prod | Security incident | Secrets only via env vars (never defaults); fail fast at startup if required secrets missing; document rotation procedure in README runbook |
| Scope creep toward notifications UI, file attachments, etc. | Delays core value | This plan deliberately excludes: email/webhook delivery (events are published but no consumer), attachments, multi-tenancy, i18n — all listed as v2 candidates below |

### 10.1 Explicitly out of scope (v2 candidates)
Notification consumers (email/Slack/webhook), ticket attachments & file storage, customer self-service portal UI, reporting/analytics dashboards, holiday-aware SLA calendars, multi-tenancy, rate limiting beyond login, background job retries with backoff queues.





