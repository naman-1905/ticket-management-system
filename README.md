# Ticket Management System

Full-stack support ticketing platform with an asynchronous FastAPI backend and a Next.js frontend. It supports customers, agents, and administrators with ticket lifecycle management, comments, SLA tracking, audit logging, JWT authentication, and role-based access control.

The backend is the current MVP contract. The frontend is being implemented toward the Beacon UX described in [frontend-implementation-plan.md](frontend-implementation-plan.md). Detailed backend behavior is documented in [backend_implementation.md](backend_implementation.md).

## Product scope

- Customers create, view, and comment on their own tickets.
- Agents manage the shared queue, assign tickets, change status, and write public or internal comments.
- Administrators manage roles, SLA policies, and audit logs.
- Tickets use the state machine `OPEN → IN_PROGRESS → ON_HOLD → RESOLVED → CLOSED`; the UI should expose only valid transitions.
- Priorities are `P1` through `P4`, with first-response and resolution deadlines from the active SLA policy.
- Ticket and comment writes support the optional `Idempotency-Key` header for safe retries.
- API errors use `{ error: { code, message, details }, request_id }`.

## Technology

### Backend

- Python 3.12+, FastAPI, Uvicorn, Pydantic v2
- SQLAlchemy 2 async ORM with PostgreSQL 16 and psycopg
- Alembic migrations
- Argon2 password hashing and PyJWT access/refresh tokens
- Structured JSON logging, request IDs, and Prometheus HTTP metrics
- Redis and RabbitMQ configured as infrastructure dependencies

### Frontend

The repository currently contains a JavaScript Next.js application. The target frontend plan specifies Next.js 16 App Router, React 19, TypeScript strict mode, Tailwind CSS v4, shadcn/ui/Radix, Lucide, Motion, Sonner, TanStack Query, Zustand, React Hook Form, Zod, and OpenAPI-generated types. The target test stack is Vitest/Testing Library plus Playwright.

The planned UI is a dense, keyboard-friendly ticket queue with dark/light themes, optimistic ticket/status/assignment/comment updates, ticket details as an intercepted slide-over or shareable full page, a `Cmd/Ctrl+K` command palette, and unmistakable public/internal comment separation.

## Run with Docker Compose

From the repository root:

```powershell
Copy-Item .env.example .env
docker compose --profile local up --build
```

On Linux/macOS or Git Bash/WSL:

```bash
./start.sh
```

The local profile starts PostgreSQL, Redis, RabbitMQ, the API, and the frontend:

- Frontend: http://localhost:3000
- API: http://localhost:8000
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- RabbitMQ management: http://localhost:15672 (`guest` / `guest`)

Stop the stack with `docker compose down`. `NEXT_PUBLIC_API_URL` defaults to `http://localhost:8000/api/v1`; set it to the public backend URL for another host. The backend's `CORS_ORIGINS` must include the deployed frontend origin.

## Run the frontend locally

```powershell
Set-Location frontend
Copy-Item .env.example .env.local
npm install
npm run dev
```

Open http://localhost:3000. New registrations create `CUSTOMER` accounts. Agents and administrators can be promoted through the backend role endpoint or administrative settings UI.

## Run the API locally

Start backing services:

```powershell
docker compose --profile local up -d postgres redis rabbitmq
```

Create a virtual environment and install dependencies:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r backend\requirements-dev.txt
Copy-Item .env.example .env
```

For an API running outside Docker, set `POSTGRES_HOST=localhost`, `REDIS_URL=redis://localhost:6379/0`, and `RABBITMQ_URL=amqp://guest:guest@localhost:5672/` in `.env`.

Run the API:

```powershell
Set-Location backend
..\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Development startup creates SQLAlchemy tables automatically. Production deployments must run `alembic upgrade head` first, use `ENVIRONMENT=production`, and provide a randomly generated `JWT_SECRET` of at least 32 characters. Never commit `.env` or production secrets.

## API overview

All versioned endpoints are under `/api/v1`. Protected requests use:

```http
Authorization: Bearer <access_token>
```

| Area | Endpoints |
|---|---|
| Authentication | `POST /auth/register`, `/auth/login`, `/auth/refresh`, `/auth/logout`; `GET /auth/me` |
| Tickets | `POST /tickets`, `GET /tickets`, `GET /tickets/{id}`, `PATCH /tickets/{id}/status`, `POST /tickets/{id}/assign` |
| Comments | `GET/POST /tickets/{id}/comments` |
| SLA | `GET /sla/policies`, `POST/PATCH /sla/policies`; `GET /tickets/{id}/sla` |
| Administration | `GET /audit/logs`; `GET /users`; `PATCH /users/{id}/role` |

Access tokens last 15 minutes by default. Refresh tokens rotate and are invalidated on reuse; a frontend refresh failure should clear the session and return to login. Login is rate-limited to five attempts per 60 seconds per client IP by default.

Operational endpoints include `/healthz`, `/health`, `/health/db`, `/api/v1/meta/version`, `/docs`, and `/redoc`. Responses include `X-Request-ID` and `X-Response-Time-Ms` headers.

## Frontend routes

| Route | Access |
|---|---|
| `/login`, `/register` | Public |
| `/tickets`, `/tickets/new`, `/tickets/[ticketId]` | All authenticated roles; ownership is enforced by the API |
| `/settings/profile` | All authenticated roles |
| `/settings/sla` | Agents read; administrators read/write |
| `/settings/audit-log` | Administrators only |
| `/settings/members` | Administrators only; role management |

Ticket details open as a slide-over from the queue and as a full page for direct navigation, refreshes, and shared links. The frontend should handle ownership-hidden `404` responses generically so ticket existence is not disclosed.

## First API request

```powershell
$body = @{ email = "customer@example.com"; full_name = "Example Customer"; password = "change-me-123" } | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/v1/auth/register -ContentType "application/json" -Body $body
```

Use the returned access token with Swagger UI's `Authorize` button. Include an `Idempotency-Key` on ticket/comment submissions and preserve `request_id` when reporting failures.

## Tests and quality checks

```powershell
.\.venv\Scripts\Activate.ps1
pytest -q
pytest --cov=backend/app
ruff check backend/app
mypy backend/app
```

Frontend test commands will be added as the planned TypeScript/TanStack Query implementation lands.

## Project layout

```text
backend/app/
├── core/                  Configuration, security, errors, logging, idempotency
├── db/                    Async SQLAlchemy setup
└── modules/
    ├── identity/          Registration, login, refresh, users, roles
    ├── ticketing/         Tickets, status, assignment, comments, events
    ├── sla/               Policies, deadlines, breach worker
    ├── audit/             Action history and admin queries
    └── notifications/     Notification model and consumer boundary

frontend/
├── app/                   App Router pages and layouts
├── components/            Auth and ticket UI components
└── lib/                   API integration
```

## Current limitations

- Redis is configured, but idempotency and login rate limiting currently use process-local memory.
- RabbitMQ is configured, but the event bus is currently in memory; events are not durable or shared across API replicas.
- Notification delivery is not implemented; publishing an event does not guarantee an email or in-app notification.
- SLA resolution breach monitoring is implemented, but first-response tracking is not automatically completed from comments.
- User activate/deactivate endpoints are not currently exposed.
- Ticket responses contain core fields; related profiles, comment counts, and expanded SLA data may require separate requests.
- The version endpoint returns `git_sha: "unknown"` unless deployment logic supplies a value.

## Deployment

Jenkins supports `PIPELINE_TARGET=frontend`, `backend`, or `both`. Backend deployments run Alembic migrations and health checks; frontend deployments build and recreate only the frontend container. A production host needs Docker Compose, the checked-out repository, environment-specific secrets, and the `Ticket-Backend-Env` Jenkins credential. Configure `CORS_ORIGINS` with the actual frontend origin.
