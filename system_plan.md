# Enterprise Ticket Management System — Revised Execution Plan

## 1. Design Philosophy

This project should be built as a **modular monolith first**, not as a collection of microservices from day one.

The original plan is valuable because it lists many production backend patterns worth learning. However, it risks becoming a technology checklist rather than an executable engineering plan. The improved plan follows these rules:

1. **Start with one well-structured FastAPI application**  
   The system should be a modular monolith with clear bounded contexts: identity, ticketing, comments, attachments, notifications, search, analytics, and background workers.

2. **Introduce distributed systems only when they solve a real problem**  
   Redis, RabbitMQ, and background workers are core because they solve concrete problems: caching, rate limiting, async emails, retries, and decoupling side effects. Kafka, MongoDB, Solr, GraphQL, and Kubernetes are valuable but should be added later only when the simpler solution is insufficient.

3. **Every phase must end with a demoable system**  
   A phase is not complete when a tool is installed. It is complete when a user can perform a realistic workflow end-to-end.

4. **Prefer boring, inspectable technology for the core path**  
   The core system should be easy to debug, test, and deploy on a single machine using Docker Compose.

5. **Evolve toward services only when there is a concrete scaling or ownership reason**  
   For example, the notification worker can later become a separate service if it needs independent scaling, different language, or independent deployment. The monolith should be designed so this extraction is possible later.

---

## 2. Core Technology Stack

The core stack should be the smallest stack that can still demonstrate production-grade backend engineering.

| Technology | Why it is core | What breaks or becomes worse without it |
|---|---|---|
| Python 3.12 + FastAPI + Pydantic v2 | Typed, async HTTP APIs, validation, OpenAPI docs, modern backend learning | Manual validation, weaker typing, less readable APIs |
| Uvicorn + Gunicorn | ASGI server for development and multi-worker production runtime | Single-process server, poor worker management, weaker graceful shutdown |
| SQLAlchemy 2.0 + asyncpg | Async ORM/database access with transactions and relationship modeling | Raw SQL everywhere, harder concurrency, harder maintenance |
| PostgreSQL | Primary ACID source of truth for users, tickets, comments, SLAs, notifications, audit | No strong relational integrity, transactions, or audit trail |
| Alembic | Managed schema migrations and safe schema evolution | Schema drift, broken local/dev/prod databases |
| Redis | Caching, rate limiting, distributed locks, job state, refresh-token revocation, temporary data | Database becomes bottleneck, no safe rate limiting, weaker concurrency control |
| RabbitMQ | Reliable task queue for email, notifications, attachment scanning, reports, retries, DLQ | Side effects block API, lost jobs, no retry/DLQ pattern |
| MinIO | S3-compatible object storage for attachments and file previews | Local filesystem does not scale and creates security/backup problems |
| ClamAV | Real virus scanning for uploaded files | File upload security remains a placeholder |
| Docker + Docker Compose | Reproducible local infrastructure and service isolation | Inconsistent environments, painful onboarding |
| GitHub Actions or Jenkins | CI/CD: lint, test, build image, deploy | Manual deployments, no automated quality gate |
| pytest + Testcontainers | Unit/integration/e2e testing against real Postgres, Redis, RabbitMQ, MinIO | Flaky tests, false confidence, hard-to-debug failures |
| structlog or loguru | Structured JSON logging with request/user/ticket context | Unparseable logs, poor debugging |
| prometheus-fastapi-instrumentator | Basic `/metrics` endpoint for HTTP, latency, error rate | No operational observability |
| APScheduler or asyncio scheduler | Scheduled SLA sweeps and periodic jobs | Missed SLA breaches, no periodic analytics aggregation |
| MailHog or equivalent | Local email capture for development/testing | No way to verify email flows locally |
| Locust or k6 | Load testing and performance validation | No evidence that the system can handle realistic traffic |

### Primary choices where the original plan had overlapping tools

| Concern | Primary choice | Optional/advanced alternative |
|---|---|---|
| Task queue vs event log | **RabbitMQ** | Kafka |
| API style | **REST** | GraphQL |
| Primary database | **PostgreSQL** | MongoDB |
| Search | **PostgreSQL full-text search** | Apache Solr |
| Deployment | **Docker Compose** | Kubernetes |
| CI/CD | **GitHub Actions** or **Jenkins**, choose one | The other if environment requires it |
| Tracing | Structured logs + request/trace IDs | OpenTelemetry |

---

## 3. Optional / Stretch Stack

These technologies are useful, but they should not block the core system from being finished.

| Technology | When to add it | Why it is optional |
|---|---|---|
| Kafka | When you need durable event replay, independent consumer groups, analytics pipelines, or high-volume event sourcing | RabbitMQ already solves task queues and async side effects for the MVP |
| MongoDB | When audit logs, activity timelines, or event snapshots become too large or too document-shaped for PostgreSQL | PostgreSQL can handle the early audit/event needs with much less operational complexity |
| Apache Solr | When PostgreSQL full-text search is insufficient for highlighting, suggestions, faceted search, or very large indexes | Postgres FTS is enough for a single-tenant MVP |
| GraphQL | When the frontend or API consumers need flexible aggregated queries | REST is simpler, easier to version, and sufficient for backend learning |
| Kubernetes | When you need multi-node deployment, autoscaling, rolling updates, service discovery, or cluster-level secrets | Docker Compose is enough for a one-person project and is far easier to debug |
| OpenTelemetry | When the system is split into services and needs distributed tracing | Request/trace IDs in logs are enough for a monolith |
| Grafana | When you want dashboards and alerting on top of Prometheus metrics | A `/metrics` endpoint is enough to prove observability |
| MLflow | When you have enough resolved-ticket data to train triage/priority models | ML before stable data and analytics is premature |
| Next.js dashboard | When you want a custom UI beyond Swagger UI | The project is backend-focused; Swagger UI is sufficient for the core |

---

## 4. Cross-Cutting Architecture Decisions

These decisions should exist from the beginning, not be bolted on later.

### 4.1 Modular Monolith Layout

Recommended structure:

```text
ticket-management-system/
  app/
    main.py
    core/
      config.py
      logging.py
      security.py
      exceptions.py
      dependencies.py
    api/
      v1/
        routers/
          auth.py
          tickets.py
          comments.py
          attachments.py
          notifications.py
          analytics.py
    application/
      identity/
      tickets/
      comments/
      attachments/
      notifications/
      analytics/
    domain/
      tickets/
      users/
      notifications/
      attachments/
    infrastructure/
      db/
      redis/
      rabbitmq/
      storage/
      email/
      search/
    workers/
      email_worker.py
      notification_worker.py
      attachment_scan_worker.py
      report_worker.py
      sla_worker.py
      outbox_publisher.py
  alembic/
  tests/
    unit/
    integration/
    e2e/
    load/
  docker/
  docs/
  .env.example
  docker-compose.yml
  Dockerfile
  pyproject.toml
```

Rules:

- API routes should be thin.
- Application services orchestrate use cases.
- Domain layer contains business rules and state machines.
- Infrastructure layer contains adapters: database, Redis, RabbitMQ, MinIO, email.
- Workers are separate processes but can live in the same repository.
- Dependencies point inward: API → application → domain ← infrastructure.

This layout allows later extraction into services without rewriting the domain logic.

---

### 4.2 API Versioning Strategy

Use URI versioning:

```text
/v1/auth/login
/v1/tickets
/v1/tickets/{id}
/v1/notifications
```

Rules:

- All public endpoints are under `/v1`.
- Changes to v1 must be additive when possible.
- Breaking changes require `/v2`.
- Deprecated endpoints should return headers such as:

```text
Deprecation: true
Sunset: 2026-12-31
```

- Pydantic response models must be stable.
- Do not expose internal SQLAlchemy objects directly.

---

### 4.3 Global Error Handling and Consistent API Error Shape

Use a global exception handler strategy from day one.

Recommended error shape:

```json
{
  "type": "https://api.example.com/problems/validation-error",
  "title": "Validation Error",
  "status": 422,
  "detail": "One or more fields are invalid.",
  "instance": "/v1/tickets",
  "request_id": "req_01J9ZK2M8N",
  "errors": [
    {
      "field": "title",
      "code": "max_length",
      "message": "Title must be at most 200 characters."
    }
  ]
}
```

Exception categories:

| HTTP Status | Meaning | Example |
|---|---|---|
| 400 | Bad request | Malformed JSON |
| 401 | Unauthenticated | Missing/invalid token |
| 403 | Forbidden | Role lacks permission |
| 404 | Not found | Ticket does not exist |
| 409 | Conflict | Invalid state transition, optimistic lock conflict |
| 422 | Validation error | Bad field value |
| 429 | Rate limited | Too many requests |
| 500 | Internal server error | Unexpected failure |

Rules:

- Never return stack traces to clients.
- Log full details internally.
- Include `request_id` in all error responses and logs.
- Use domain exceptions such as:
  - `TicketStateTransitionError`
  - `InvalidTicketOperationError`
  - `AttachmentScanFailedError`
  - `RefreshTokenReuseDetectedError`

---

### 4.4 Authentication, Refresh Token Rotation, and Revocation

Core auth design:

- Access token:
  - JWT
  - Short-lived: 5–15 minutes
  - Contains `sub`, `role`, `jti`, `exp`, `iat`
- Refresh token:
  - Opaque token
  - Stored hashed in PostgreSQL
  - Longer-lived: 7–30 days
  - Single-use
  - Rotated on every refresh
  - Has `family_id` for reuse detection

Refresh token rotation strategy:

1. User logs in.
2. System creates:
   - Access token
   - Refresh token
   - Refresh token family ID
3. User calls refresh endpoint.
4. System validates the refresh token.
5. If valid:
   - Mark old refresh token as used.
   - Create new refresh token in the same family.
   - Return new access + refresh tokens.
6. If an already-used refresh token is presented:
   - Treat as possible theft.
   - Revoke the entire refresh token family.
   - Require password reset or re-login.

Revocation:

- Logout revokes the current refresh token.
- Password change revokes all active refresh tokens for the user.
- Admin can revoke user sessions.
- Short-lived access tokens can be tolerated to expire naturally.
- Optional Redis `jti` blacklist can immediately invalidate access tokens for high-risk actions.

RBAC:

- Roles: `USER`, `AGENT`, `ADMIN`
- Permission examples:
  - `ticket:create`
  - `ticket:assign`
  - `ticket:escalate`
  - `ticket:comment:internal`
  - `admin:user:manage`
  - `admin:sla:manage`

Use FastAPI dependencies for permission checks:

```python
async def require_permission(
    permission: str,
    current_user: User = Depends(get_current_user),
):
    if not current_user.has_permission(permission):
        raise ForbiddenError(...)
    return current_user
```

---

### 4.5 Alembic Migration Strategy

Use Alembic for all schema changes.

Rules:

- Never edit applied migrations.
- Always generate migrations with autogenerate, then review manually.
- Every migration should have a sensible `downgrade()` where possible.
- Seed data migrations should be idempotent.
- CI must run migrations against a fresh test database.
- Avoid destructive migrations in one step when possible.

Example safe column addition:

1. Add nullable column.
2. Deploy.
3. Backfill data if needed.
4. Add index/constraints if needed.
5. Make column non-null in a later migration.

Migrations should cover:

- `users`
- `refresh_tokens`
- `categories`
- `priorities`
- `sla_rules`
- `tickets`
- `ticket_status_history`
- `ticket_assignments`
- `comments`
- `attachments`
- `notifications`
- `audit_logs`
- `outbox_events`
- `idempotency_keys`
- `processed_jobs`

---

### 4.6 Testing Strategy

Testing should be layered.

| Layer | Purpose | Tools |
|---|---|---|
| Unit tests | Domain logic, state machine, SLA math, token rotation | pytest |
| Integration tests | API + database + Redis + RabbitMQ + MinIO | pytest, Testcontainers, httpx |
| E2E tests | Full user journeys | pytest, httpx, MailHog |
| Load tests | Performance under concurrent load | Locust or k6 |
| Contract tests | RabbitMQ message shape, API response shape | pytest, JSON Schema |

Test database strategy:

- Use Testcontainers for:
  - PostgreSQL
  - Redis
  - RabbitMQ
  - MinIO
  - ClamAV, if needed in tests
- Each test should start from a known state.
- Prefer transaction rollback for fast Postgres tests when possible.
- For Redis, flush test database or use a unique key prefix.
- For RabbitMQ, create test queues and purge between tests.
- For MinIO, create test buckets and delete objects after tests.

Coverage targets:

- Overall backend coverage: at least 80%
- Auth, ticket state machine, SLA engine, idempotency: at least 90%
- Worker handlers: at least 85%
- Do not chase 100% in generated schema code or infrastructure adapters.

Critical tests to include:

- Register → verify → login → refresh → logout
- Refresh token reuse detection
- Ticket state transitions allowed and denied
- Optimistic locking conflict returns 409
- SLA deadline calculation
- SLA breach detection
- Duplicate RabbitMQ message does not duplicate notification
- Virus scan blocks infected file
- Search/filter/pagination correctness
- RBAC enforcement
- Rate limiting behavior

---

### 4.7 Structured Logging and Correlation IDs

Add structured logging from Phase 0.

Requirements:

- JSON logs in production.
- Human-readable logs in development, if desired.
- Every request gets a `request_id`.
- Use `X-Request-ID` header.
- If missing, generate one.
- Include request ID in:
  - Access logs
  - Application logs
  - Error responses
  - RabbitMQ message headers
  - Worker logs
  - Email headers, where useful

Recommended log fields:

```json
{
  "timestamp": "2026-01-01T12:00:00Z",
  "level": "INFO",
  "message": "ticket.assigned",
  "request_id": "req_123",
  "user_id": "usr_1",
  "ticket_id": "tkt_1001",
  "event": "ticket.status_changed",
  "from_status": "ASSIGNED",
  "to_status": "IN_PROGRESS",
  "duration_ms": 42
}
```

Rules:

- Mask emails and tokens.
- Do not log passwords or refresh tokens.
- Use structured events, not only string messages.
- OpenTelemetry can be added later for distributed tracing.

---

### 4.8 Idempotency Strategy

Idempotency is required in two places:

1. API mutations
2. Background job processing

#### API idempotency

For safe retryable endpoints such as ticket creation:

```http
POST /v1/tickets
Idempotency-Key: 3f2b1c9a-...
```

Storage table:

```text
idempotency_keys
  key
  user_id
  route
  method
  request_hash
  response_status
  response_body
  created_at
  expires_at
```

Behavior:

- If key is new, process request and store response.
- If key exists and request hash matches, return stored response.
- If key exists but request hash differs, return 409 or 422.
- Expire keys after 24–72 hours.

#### Background job idempotency

Table:

```text
processed_jobs
  id
  job_type
  event_id
  message_id
  idempotency_key
  status
  attempts
  last_error
  processed_at
```

Rules:

- Every domain event should have a stable `event_id`.
- Every RabbitMQ message should carry:
  - `message_id`
  - `event_id`
  - `request_id`
- Worker checks `processed_jobs` before doing work.
- If already processed successfully, ack and skip.
- If failed, retry with exponential backoff.
- After max retries, route to DLQ.
- Use a unique constraint on `(job_type, idempotency_key)` to prevent duplicate processing.

This is the specific background-job idempotency strategy.

---

### 4.9 File Upload Storage and Virus Scanning

Use MinIO as the primary object store.

Flow:

1. Client requests an upload URL.
2. API validates:
   - File type
   - File size
   - User permission
3. API creates a presigned MinIO PUT URL.
4. Client uploads directly to MinIO.
5. Client calls API to finalize attachment.
6. API stores metadata in PostgreSQL.
7. Worker sends attachment to ClamAV.
8. Worker updates status:
   - `PENDING`
   - `SCANNING`
   - `CLEAN`
   - `INFECTED`
   - `FAILED`
9. Download is allowed only for `CLEAN` attachments.

Rules:

- Max file size: 10 MB by default.
- Allowed types: PDF, PNG, JPG, CSV, TXT, ZIP, if needed.
- Store SHA256.
- Store original filename, content type, size.
- Use presigned download URLs with short expiry.
- Quarantine infected files.
- Never store production files on local disk.
- Local filesystem can be an adapter for unit tests only.

ClamAV should run as a Docker service.

---

### 4.10 SLA Breach Detection Mechanism

Use both event-driven and scheduled checks.

Event-driven:

- When ticket is assigned.
- When status changes.
- When priority/category changes.
- When ticket moves into a waiting state.

Scheduled sweep:

- Worker runs every 60 seconds.
- Finds tickets where:
  - status is active
  - `sla_deadline < now`
  - no breach record exists
- Emits idempotent `ticket.sla_breached` event.
- Sends notification to assignee/admin.

SLA rule model:

```text
sla_rules
  id
  category_id
  priority
  target_response_minutes
  target_resolution_minutes
  business_hours_only
  created_at
  updated_at
```

Breach record model:

```text
ticket_sla_breaches
  id
  ticket_id
  breach_type
  breached_at
  detected_at
  event_id
  notified
```

Unique constraint:

```text
(ticket_id, breach_type)
```

This prevents duplicate breach events.

---

### 4.11 Rate Limiting and Concurrency Control

Use Redis for:

- Rate limiting
- Distributed locks
- Job state
- Cache
- Temporary tokens
- Session revocation

Rate limiting strategy:

- Login: strict limit, e.g. 5 attempts per minute per user/IP.
- Ticket creation: e.g. 20 per hour per user.
- General API: e.g. 300 requests per minute per user/IP.
- Admin endpoints: stricter limits.

Implementation:

- Token bucket or sliding window in Redis.
- Return 429 with:

```json
{
  "type": "https://api.example.com/problems/rate-limited",
  "title": "Rate Limited",
  "status": 429,
  "detail": "Too many requests. Try again later.",
  "request_id": "req_123",
  "retry_after_seconds": 30
}
```

Concurrency control:

- Use optimistic locking for ticket updates:
  - `tickets.version`
  - `UPDATE tickets SET ... WHERE id = :id AND version = :expected_version`
  - If no row updated, return 409.
- Use Redis distributed lock for long-running singleton jobs:
  - SLA sweep
  - report generation
  - cache rebuild

---

### 4.12 Secrets Management

Development:

- `.env` file, not committed.
- `.env.example` committed.
- Docker Compose reads `.env`.

Production:

- Use one of:
  - SOPS-encrypted environment files
  - HashiCorp Vault
  - Kubernetes Secrets, if using Kubernetes
  - CI/CD provider encrypted variables
- Never commit:
  - Database passwords
  - Redis passwords
  - RabbitMQ passwords
  - MinIO keys
  - JWT signing keys
  - SMTP credentials
- Rotate secrets regularly.

Minimum required secrets:

```text
POSTGRES_PASSWORD
REDIS_PASSWORD
RABBITMQ_PASSWORD
MINIO_ROOT_PASSWORD
JWT_ACCESS_SECRET
JWT_REFRESH_SECRET
SMTP_PASSWORD
```

---

## 5. Core Phases

These phases are required for the project to be considered done and resume-worthy.

---

### Core Phase 0 — Foundation and Platform Skeleton

**Goal:** Create a stable, observable, testable FastAPI base.

**What gets built:**

- FastAPI app factory
- Pydantic settings
- Docker Compose for:
  - PostgreSQL
  - Redis
  - RabbitMQ
  - MinIO
  - ClamAV
  - MailHog
- Structured logging
- Request ID middleware
- Global exception handlers
- `/v1/health`
- `/v1/ready`
- `/metrics`
- Alembic setup
- Initial migration
- CI pipeline:
  - lint
  - type check
  - unit tests
  - Docker build

**Demoable at the end:**

```bash
docker compose up
curl http://localhost:8000/v1/health
curl http://localhost:8000/metrics
```

You can see:

- Structured logs with request IDs
- Database migration applied
- Redis, RabbitMQ, MinIO healthy
- OpenAPI docs
- CI passing

**Dependencies:** None.

**Acceptance criteria:**

- `docker compose up --build` works cleanly.
- Health endpoint reports dependencies.
- Logs are JSON and include `request_id`.
- Alembic migration runs successfully.
- Tests run in CI.

---

### Core Phase 1 — Identity, Authentication, and RBAC

**Goal:** Build a secure identity foundation.

**What gets built:**

- User model
- Role model
- Password hashing
- Registration
- Email verification
- Login
- Logout
- Refresh token rotation
- Refresh token revocation
- Password reset
- Change password
- RBAC middleware
- Rate limiting for auth endpoints
- Audit log for security events

**Key endpoints:**

```text
POST /v1/auth/register
POST /v1/auth/login
POST /v1/auth/refresh
POST /v1/auth/logout
POST /v1/auth/verify-email
POST /v1/auth/resend-verification
POST /v1/auth/request-password-reset
POST /v1/auth/reset-password
PUT /v1/users/me/password
```

**Demoable at the end:**

- Register user.
- Verify email from MailHog.
- Login.
- Access protected endpoint.
- Refresh token works once.
- Reusing old refresh token revokes family.
- Logout revokes refresh token.
- Password reset works.
- Agent and admin roles can access role-specific endpoints.

**Dependencies:** Phase 0.

**Acceptance criteria:**

- Passwords are never stored in plaintext.
- Refresh token reuse detection works.
- RBAC returns 403 correctly.
- Login is rate limited.
- Security audit logs are written.

---

### Core Phase 2 — Ticket Domain Core

**Goal:** Build the core ticket lifecycle.

**What gets built:**

- Categories
- Priorities
- SLA rules
- Tickets
- Ticket state machine
- Ticket status history
- Ticket assignment
- Reassignment
- Escalation
- Closure
- Reopening
- Cancellation
- Optimistic locking
- Transactional outbox events
- Basic REST endpoints
- Basic pagination

**Ticket states:**

```text
OPEN
ASSIGNED
IN_PROGRESS
WAITING_FOR_CUSTOMER
ESCALATED
RESOLVED
CLOSED
REOPENED
CANCELLED
```

**Allowed transitions should be explicit.**

Example:

```text
OPEN -> ASSIGNED
OPEN -> CANCELLED
ASSIGNED -> IN_PROGRESS
ASSIGNED -> WAITING_FOR_CUSTOMER
IN_PROGRESS -> WAITING_FOR_CUSTOMER
IN_PROGRESS -> RESOLVED
ESCALATED -> IN_PROGRESS
RESOLVED -> CLOSED
RESOLVED -> REOPENED
REOPENED -> IN_PROGRESS
```

**Endpoints:**

```text
POST /v1/tickets
GET /v1/tickets
GET /v1/tickets/{id}
PATCH /v1/tickets/{id}
POST /v1/tickets/{id}/assign
POST /v1/tickets/{id}/reassign
POST /v1/tickets/{id}/escalate
POST /v1/tickets/{id}/resolve
POST /v1/tickets/{id}/close
POST /v1/tickets/{id}/reopen
POST /v1/tickets/{id}/cancel
GET /v1/tickets/{id}/history
```

**Demoable at the end:**

- User creates a ticket.
- Agent sees assigned ticket.
- Agent changes status.
- Invalid transition returns 409.
- Two concurrent updates cause optimistic lock conflict.
- Status history is recorded.
- Outbox events are written transactionally.

**Dependencies:** Phase 1.

**Acceptance criteria:**

- All state transitions are validated.
- Invalid transitions are rejected.
- Ticket number is unique.
- SLA deadline is calculated.
- Concurrent update conflict returns 409.
- Domain events are stored in `outbox_events`.

---

### Core Phase 3 — Comments, Mentions, and Attachments

**Goal:** Add collaboration and file handling.

**What gets built:**

- Public comments
- Internal comments
- Edit comment
- Delete comment
- Mention parsing
- Attachment upload
- Attachment metadata
- MinIO presigned upload/download
- ClamAV scanning
- Quarantine infected files
- Attachment status workflow

**Endpoints:**

```text
POST /v1/tickets/{id}/comments
PATCH /v1/comments/{id}
DELETE /v1/comments/{id}

POST /v1/tickets/{id}/attachments
GET /v1/attachments/{id}
GET /v1/attachments/{id}/download
DELETE /v1/attachments/{id}
```

**Demoable at the end:**

- User adds public comment.
- Agent adds internal comment.
- User cannot read internal comments.
- User uploads PDF.
- ClamAV scans file.
- Infected file is blocked.
- Clean file can be downloaded.
- Attachment metadata shows scan status.

**Dependencies:** Phase 2.

**Acceptance criteria:**

- Internal comments are hidden from users.
- File upload does not bypass size/type validation.
- Infected file is not downloadable.
- Download URLs are short-lived.
- Attachment events are written to outbox.

---

### Core Phase 4 — Search, Filtering, Pagination, and Caching

**Goal:** Make ticket retrieval fast and production-like.

**What gets built:**

- PostgreSQL full-text search
- Search on:
  - Title
  - Description
  - Comments
- Filters:
  - Status
  - Priority
  - Category
  - Date range
  - Assigned agent
  - Created by
- Sorting:
  - Latest
  - Oldest
  - Highest priority
  - SLA breach
- Cursor pagination
- Offset pagination
- Redis cache-aside pattern
- Cache invalidation on writes
- TTL strategy

**Endpoints:**

```text
GET /v1/tickets?search=...&status=...&priority=...
GET /v1/search/tickets
```

**Cache strategy:**

```text
Read:
  Request -> Redis lookup -> Hit -> Return
                         -> Miss -> PostgreSQL -> Populate Redis -> Return

Write:
  Update PostgreSQL -> Invalidate Redis -> Rebuild if needed
```

**Demoable at the end:**

- Search tickets by title/description/comment.
- Filter by status/priority/category/agent.
- Sort by SLA breach.
- Cursor pagination works.
- Repeated list request hits Redis.
- Updating a ticket invalidates cache.

**Dependencies:** Phases 2 and 3.

**Acceptance criteria:**

- Search is correct and indexed.
- Pagination is stable.
- Cache hit/miss is observable in logs.
- Cache invalidation works.
- List endpoint p95 latency is acceptable under load.

---

### Core Phase 5 — Async Jobs, Notifications, and Reliable Workers

**Goal:** Move side effects out of the request path.

**What gets built:**

- RabbitMQ topology
- Outbox publisher
- Worker processes
- Email sending
- In-app notifications
- Attachment scan worker
- Report generation worker
- Retry mechanism
- Dead letter queue
- Job idempotency
- Job state tracking

**RabbitMQ queues:**

```text
ticket.events
notifications.email
notifications.inapp
attachments.scan
reports.generate
dlq.failed
```

**Message envelope:**

```json
{
  "event_id": "evt_123",
  "event_type": "ticket.created",
  "aggregate_type": "Ticket",
  "aggregate_id": "tkt_1001",
  "request_id": "req_123",
  "occurred_at": "2026-01-01T12:00:00Z",
  "data": {}
}
```

**Outbox pattern:**

```text
Business transaction:
  1. Update ticket in PostgreSQL
  2. Write outbox_event in same transaction

Relay process:
  1. Read unpublished outbox events
  2. Publish to RabbitMQ
  3. Mark published

Worker:
  1. Consume message
  2. Check idempotency
  3. Process
  4. Ack or retry
```

**Demoable at the end:**

- Creating a ticket sends an email asynchronously.
- Assigning a ticket creates an in-app notification.
- Duplicate message does not create duplicate notification.
- Worker failure triggers retry.
- After max retries, message goes to DLQ.
- Attachment scan happens in background.
- CSV report generation works.

**Dependencies:** Phases 2, 3, and 4.

**Acceptance criteria:**

- API does not wait for email sending.
- Duplicate events are idempotent.
- DLQ works.
- Retries use exponential backoff.
- Workers are restart-safe.
- Notification status is visible.

---

### Core Phase 6 — SLA Enforcement and Analytics

**Goal:** Add business-rule enforcement and operational reporting.

**What gets built:**

- SLA rule engine
- SLA deadline calculation
- SLA breach detection
- SLA breach notifications
- Scheduled sweep worker
- Analytics aggregation
- Dashboard endpoints
- Basic metrics
- Agent performance reporting

**Analytics endpoints:**

```text
GET /v1/analytics/overview
GET /v1/analytics/tickets-by-category
GET /v1/analytics/agent-performance
GET /v1/analytics/sla-breaches
GET /v1/analytics/daily-active-users
```

**Aggregates to maintain:**

- Tickets created per day
- Tickets resolved per day
- Average resolution time
- Tickets by category
- SLA breaches
- Agent assignment count
- Agent resolution count
- Daily active users

**Demoable at the end:**

- SLA breach is detected after deadline.
- Breach notification is sent.
- Dashboard shows correct counts.
- `/metrics` exposes request latency/error rate.
- Agent performance report is generated.

**Dependencies:** Phase 5.

**Acceptance criteria:**

- SLA breach is idempotent.
- Dashboard reads are fast.
- Metrics are available.
- Reports are generated asynchronously.
- Analytics do not scan raw tables repeatedly.

---

### Core Phase 7 — Production Hardening, CI/CD, and Deployment

**Goal:** Make the system deployable and operationally credible.

**What gets built:**

- Multi-stage Docker build
- Gunicorn + Uvicorn worker configuration
- Graceful shutdown
- Health checks
- Ready checks
- Timeouts
- Connection pooling
- Secrets management
- Backup/restore for PostgreSQL and MinIO
- Load testing
- Performance tuning
- Architecture documentation
- LLD/HLD
- Runbook
- Final CI/CD pipeline

**Deployment target:**

- Single-node Docker Compose deployment
- Optional Kubernetes deployment in stretch phase

**CI/CD pipeline:**

```text
Git push
  -> install dependencies
  -> lint
  -> type check
  -> unit tests
  -> integration tests
  -> e2e tests
  -> build Docker image
  -> push image
  -> deploy to target environment
```

**Demoable at the end:**

```bash
docker compose up --build
```

Then:

- Create ticket
- Assign ticket
- Upload file
- Trigger email
- Trigger SLA breach
- View analytics
- View metrics
- Run load test
- Restore backup

**Dependencies:** All previous core phases.

**Acceptance criteria:**

- CI is green.
- Docker image builds from scratch.
- Load test meets defined targets.
- Backup and restore work.
- Documentation explains architecture and operations.

---

## 6. Stretch Phases

These phases are valuable but should only start after the core system is stable.

---

### Stretch Phase S1 — GraphQL API

**Goal:** Provide a flexible query API for clients that need aggregated data.

**Build:**

- GraphQL schema
- Query:
  - tickets
  - ticket by ID
  - comments
  - notifications
- Mutations:
  - create ticket
  - assign ticket
  - add comment
- Optional subscriptions:
  - ticket.updated
  - notification.created

**Demo:**

```graphql
query {
  ticket(id: "tkt_1001") {
    title
    status
    comments {
      body
      author {
        name
      }
    }
  }
}
```

**Why optional:** REST is enough for the core backend learning goal. GraphQL adds schema, complexity, authorization, and N+1 management.

**Dependencies:** Core Phases 2–5.

---

### Stretch Phase S2 — Kafka Event Log and Event-Driven Consumers

**Goal:** Add a durable event log with replay and independent consumers.

**Build:**

- Kafka topics:
  - `ticket.events`
  - `user.events`
  - `notification.events`
- Producer with idempotence
- Consumer groups:
  - audit consumer
  - analytics consumer
  - search consumer
- Event replay
- Schema validation
- Ordering guarantees where needed

**Demo:**

- Replay ticket events.
- Rebuild audit timeline.
- Rebuild analytics aggregate.
- Run multiple consumer groups independently.

**Why optional:** RabbitMQ already handles task queues, retries, DLQ, and idempotency. Kafka is justified when you need replay, partitioning, and long-lived event history.

**Dependencies:** Core Phase 5.

---

### Stretch Phase S3 — MongoDB for Audit and Event Snapshots

**Goal:** Store high-volume append-only audit/event data outside PostgreSQL.

**Build:**

- MongoDB collections:
  - `audit_logs`
  - `activity_timelines`
  - `event_snapshots`
- TTL indexes
- Aggregation pipelines
- Event snapshot queries
- Optional sharding design doc

**Demo:**

- Ingest high-volume audit events.
- Query user activity timeline.
- Reconstruct ticket state from snapshots.

**Why optional:** PostgreSQL can store audit logs for the MVP. MongoDB is useful when audit/event volume becomes large or document-shaped.

**Dependencies:** Core Phase 5 or Stretch S2.

---

### Stretch Phase S4 — Apache Solr Search Service

**Goal:** Add advanced search features beyond PostgreSQL FTS.

**Build:**

- Solr core/schema
- Ticket index
- Comment index
- Faceted search
- Highlighting
- Search suggestions
- Index sync worker
- Search fallback to Postgres if Solr is down

**Demo:**

- Search with highlights.
- Faceted counts by status/category.
- Typo-tolerant suggestions.
- Full reindex from database or Kafka events.

**Why optional:** Postgres FTS is enough for a single-tenant MVP. Solr is useful when search becomes a product feature.

**Dependencies:** Core Phase 4, optionally Stretch S2.

---

### Stretch Phase S5 — Microservice Extraction and Kubernetes

**Goal:** Extract services only where there is a concrete reason.

**Possible extraction:**

1. Notification service
2. Worker service
3. Search service
4. Analytics service

**Reason to extract:**

- Independent scaling
- Independent deployment
- Different technology
- Team ownership
- Isolation of failure

**Build:**

- API Gateway
- Auth service
- Ticket service
- Notification service
- Worker service
- Kubernetes manifests
- Ingress
- Services
- ConfigMaps
- Secrets
- Persistent Volumes
- HPA
- PodDisruptionBudget
- Liveness/readiness probes

**Demo:**

- Scale notification service independently.
- Scale worker service independently.
- Rolling update without downtime.
- HPA scales under load.

**Why optional:** A modular monolith can scale horizontally with multiple API instances and worker instances. Kubernetes adds significant operational complexity and is only justified after the monolith is stable.

**Dependencies:** Core Phase 7, optionally Stretch S2.

---

### Stretch Phase S6 — MLflow and Smart Triage

**Goal:** Add predictive assistance after enough data exists.

**Build:**

- Dataset from resolved tickets
- Features:
  - category
  - priority
  - title keywords
  - description length
  - attachment count
  - user history
  - historical SLA breach rate
- Model:
  - classify priority
  - classify category
  - predict escalation risk
  - predict SLA breach risk
- MLflow tracking
- Model evaluation
- Inference endpoint or worker

**Demo:**

- New ticket gets suggested priority.
- Ticket gets escalation-risk score.
- Model metrics are tracked in MLflow.

**Why optional:** ML before stable data and analytics is premature. This should come after analytics and SLA data are reliable.

**Dependencies:** Core Phase 6.

---

### Stretch Phase S7 — Python Concurrency and Operations Lab

**Goal:** Demonstrate advanced Python runtime behavior in realistic backend tasks.

**Build:**

- Multiprocessing for large report generation
- Subprocess for PDF generation or CSV export
- Thread pool for I/O-bound external calls
- Garbage collection monitoring
- Memory usage tracking
- Large object cleanup
- Memory leak test

**Demo:**

- Generate large CSV using subprocess.
- Generate PDF using external command.
- Run memory-heavy aggregation in worker.
- Show GC and memory metrics.

**Why optional:** This is a useful learning addition, but it should not block the core system.

**Dependencies:** Core Phase 5 or 6.

---

## 7. Suggested Definition of Done for Core Project

The core project is done when:

1. `docker compose up --build` starts the full local stack.
2. Swagger UI is available.
3. Structured logs include request IDs.
4. Alembic migrations run cleanly.
5. Authentication and RBAC work.
6. Ticket lifecycle works end-to-end.
7. Comments and attachments work.
8. Search, filters, and pagination work.
9. Redis caching works.
10. RabbitMQ background jobs work.
11. Email and in-app notifications work.
12. Retries and DLQ work.
13. Idempotency works for API and workers.
14. SLA breach detection works.
15. Analytics endpoints work.
16. `/metrics` works.
17. Load test passes defined targets.
18. CI/CD pipeline passes.
19. Documentation includes:
    - Architecture diagram
    - LLD
    - HLD
    - Runbook
    - API docs
20. Tests cover critical paths.

---

## 8. What We Deliberately Left Out and Why

### 8.1 Kafka in the core plan

**Left out initially because:** RabbitMQ already solves the immediate problems: task queueing, retries, DLQ, idempotency, and async side effects.

**Add later when:** you need event replay, partitioned event streams, independent consumer groups, or high-volume analytics pipelines.

---

### 8.2 MongoDB in the core plan

**Left out initially because:** PostgreSQL can store audit logs, activity timelines, and event snapshots for the MVP.

**Add later when:** audit/event data volume becomes large, document-shaped, or too expensive to keep in the primary relational database.

---

### 8.3 Apache Solr in the core plan

**Left out initially because:** PostgreSQL full-text search is sufficient for title, description, and comment search.

**Add later when:** you need advanced highlighting, suggestions, faceted search, typo tolerance, or very large indexes.

---

### 8.4 GraphQL in the core plan

**Left out initially because:** REST is simpler to build, test, version, and secure. It also matches the learning goal of production backend APIs.

**Add later when:** clients need flexible aggregated queries or a unified API for a complex frontend.

---

### 8.5 Kubernetes in the core plan

**Left out initially because:** Docker Compose is enough to prove the architecture, test the system, and deploy to a single node.

**Add later when:** you need autoscaling, multi-node deployment, rolling updates, service discovery, or cluster-level secret management.

---

### 8.6 Seven microservices from day one

**Left out because:** splitting early creates unnecessary complexity: service-to-service auth, API gateway, distributed tracing, network failures, deployment order, and debugging difficulty.

**Add later only when:** a component has a concrete scaling, deployment, or ownership reason.

---

### 8.7 MLflow early

**Left out initially because:** machine learning needs stable data, labels, analytics, and operational context.

**Add later when:** ticket volume and resolved-ticket data are sufficient to train useful models.

---

### 8.8 Custom Next.js frontend in the core plan

**Left out because:** the goal is backend engineering, not frontend complexity.

**Use instead:** Swagger UI, API docs, and a small test client. A Next.js dashboard can be added later as a separate stretch phase.

---

## 9. Final Recommended Build Order

```text
Core Phase 0: Foundation
Core Phase 1: Auth and RBAC
Core Phase 2: Ticket domain
Core Phase 3: Comments and attachments
Core Phase 4: Search and caching
Core Phase 5: RabbitMQ workers and notifications
Core Phase 6: SLA and analytics
Core Phase 7: Production hardening and CI/CD

Stretch S1: GraphQL
Stretch S2: Kafka
Stretch S3: MongoDB
Stretch S4: Solr
Stretch S5: Kubernetes and service extraction
Stretch S6: MLflow
Stretch S7: Python concurrency/ops lab
```

This order ensures that every new technology is introduced only after the problem it solves is visible and the surrounding system is testable.
