# Ticket Management System

A full-stack ticket management system built with **Next.js** and **FastAPI**, using **PostgreSQL** as the only backend infrastructure dependency.

## Architecture

```text
┌──────────────────────────────┐
│          Frontend            │
│          Next.js             │
│        localhost:3000        │
└──────────────┬───────────────┘
               │ HTTP/REST
               ▼
┌──────────────────────────────┐
│           Backend            │
│           FastAPI            │
│        localhost:8000        │
└──────────────┬───────────────┘
               │ PostgreSQL
               ▼
┌──────────────────────────────┐
│         PostgreSQL           │
│        192.168.1.38:5432     │
│        Database: ticketing_db│
└──────────────────────────────┘
```

## Project Structure

```text
ticket-management-system/
│
├── backend/
│   ├── .venv/
│   ├── .env
│   ├── requirements.txt
│   ├── README.md
│   │
│   └── app/
│       ├── __init__.py
│       ├── config.py
│       ├── db.py
│       ├── deps.py
│       ├── main.py
│       ├── models.py
│       ├── schemas.py
│       ├── security.py
│       ├── utils.py
│       │
│       └── routers/
│           ├── __init__.py
│           ├── auth.py
│           ├── users.py
│           ├── tickets.py
│           ├── sla.py
│           └── audit.py
│
├── frontend/
│   ├── app/
│   ├── lib/
│   ├── public/
│   ├── package.json
│   └── ...
│
├── compose.yaml
├── Jenkinsfile
├── start.bat
├── start.sh
└── README.md
```

## Technology Stack

### Frontend

* Next.js
* React
* JavaScript
* Next.js App Router

### Backend

* FastAPI
* Python
* SQLAlchemy 2
* asyncpg
* Pydantic
* JWT authentication
* Argon2 password hashing

### Database

* PostgreSQL 18
* Database: `ticketing_db`
* Host: `192.168.1.38`
* Port: `5432`
* User: `naman`

### Infrastructure

The backend intentionally uses PostgreSQL as its only external infrastructure dependency.

Not used:

* Redis
* RabbitMQ
* Celery
* Kafka
* Prometheus
* Alembic

Database tables are created automatically by SQLAlchemy when the backend starts.

---

# Backend

## Requirements

* Python 3.12+
* PostgreSQL
* PostgreSQL must be reachable from the development machine on port `5432`

## Backend Setup

From the project root:

```cmd
cd backend
```

Create the virtual environment:

```cmd
python -m venv .venv
```

Activate it in Windows CMD:

```cmd
.venv\Scripts\activate.bat
```

Verify Python:

```cmd
where python
```

The first result should be:

```text
D:\Projects\ticket-management-system\backend\.venv\Scripts\python.exe
```

Install dependencies:

```cmd
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Backend Environment

Create:

```text
backend/.env
```

Example:

```env
DATABASE_URL=postgresql+asyncpg://naman:YOUR_PASSWORD@192.168.1.38:5432/ticketing_db

JWT_SECRET_KEY=YOUR_GENERATED_SECRET

ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=30

APP_VERSION=1.0.0
```

Do not commit `.env`.

The PostgreSQL password and JWT secret must never be committed to source control.

## Generate JWT Secret

Generate a strong secret with:

```cmd
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

Copy the generated value into:

```env
JWT_SECRET_KEY=...
```

## Verify Database Configuration

Run:

```cmd
python -c "from app.config import settings; from sqlalchemy.engine import make_url; u=make_url(settings.database_url); print('driver:',u.drivername); print('host:',u.host); print('port:',u.port); print('database:',u.database); print('username:',u.username)"
```

Expected:

```text
driver: postgresql+asyncpg
host: 192.168.1.38
port: 5432
database: ticketing_db
username: naman
```

## Test PostgreSQL Connectivity

From Windows:

```cmd
powershell -Command "Test-NetConnection 192.168.1.38 -Port 5432"
```

Expected:

```text
TcpTestSucceeded : True
```

## Start Backend

```cmd
cd backend
.venv\Scripts\activate.bat
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Backend:

```text
http://localhost:8000
```

Swagger UI:

```text
http://localhost:8000/docs
```

OpenAPI:

```text
http://localhost:8000/openapi.json
```

---

# Frontend

## Requirements

* Node.js
* npm

## Install Dependencies

```cmd
cd frontend
npm install
```

## Start Development Server

```cmd
npm run dev
```

Frontend:

```text
http://localhost:3000
```

The frontend API URL should point to the FastAPI backend.

Example:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
```

---

# Start Everything

## Windows

The project contains:

```text
start.bat
```

Run from the project root:

```cmd
start.bat
```

This starts:

```text
Frontend → http://localhost:3000
Backend  → http://localhost:8000
```

The backend and frontend run in separate terminal windows so their logs remain independent.

## WSL / Linux

The project also contains:

```text
start.sh
```

Make it executable:

```bash
chmod +x start.sh
```

Run:

```bash
./start.sh
```

---

# API

All versioned API routes use:

```text
/api/v1
```

## Root & Health

| Method | Endpoint               | Auth | Purpose                   |
| ------ | ---------------------- | ---- | ------------------------- |
| GET    | `/`                    | —    | Service banner            |
| GET    | `/healthz`             | —    | Liveness + database state |
| GET    | `/health`              | —    | Liveness + database state |
| GET    | `/health/db`           | —    | Database health           |
| GET    | `/api/v1/meta/version` | —    | Application version       |

## Authentication

| Method | Endpoint                | Auth   |
| ------ | ----------------------- | ------ |
| POST   | `/api/v1/auth/register` | Public |
| POST   | `/api/v1/auth/login`    | Public |
| POST   | `/api/v1/auth/refresh`  | Public |
| POST   | `/api/v1/auth/logout`   | Bearer |
| GET    | `/api/v1/auth/me`       | Bearer |

Authentication uses:

```text
Authorization: Bearer <access_token>
```

Roles:

```text
CUSTOMER
AGENT
ADMIN
```

## Users

| Method | Endpoint                       | Roles        |
| ------ | ------------------------------ | ------------ |
| GET    | `/api/v1/users`                | AGENT, ADMIN |
| PATCH  | `/api/v1/users/{user_id}/role` | ADMIN        |

## Tickets

| Method | Endpoint                               | Roles                  |
| ------ | -------------------------------------- | ---------------------- |
| POST   | `/api/v1/tickets`                      | Any authenticated user |
| GET    | `/api/v1/tickets`                      | Any authenticated user |
| GET    | `/api/v1/tickets/{ticket_id}`          | Any authenticated user |
| PATCH  | `/api/v1/tickets/{ticket_id}/status`   | Authenticated          |
| POST   | `/api/v1/tickets/{ticket_id}/assign`   | AGENT, ADMIN           |
| GET    | `/api/v1/tickets/{ticket_id}/comments` | Authenticated          |
| POST   | `/api/v1/tickets/{ticket_id}/comments` | Authenticated          |
| GET    | `/api/v1/tickets/{ticket_id}/sla`      | Authenticated          |

Customers are restricted to their own tickets.

Agents and administrators can work with tickets across customers.

## SLA

| Method | Endpoint                           | Roles        |
| ------ | ---------------------------------- | ------------ |
| GET    | `/api/v1/sla/policies`             | AGENT, ADMIN |
| POST   | `/api/v1/sla/policies`             | ADMIN        |
| PATCH  | `/api/v1/sla/policies/{policy_id}` | ADMIN        |

## Audit

| Method | Endpoint             | Roles |
| ------ | -------------------- | ----- |
| GET    | `/api/v1/audit/logs` | ADMIN |

---

# Authentication Flow

## Register

```http
POST /api/v1/auth/register
```

```json
{
  "email": "user@example.com",
  "full_name": "Jane Doe",
  "password": "min-8-chars"
}
```

Returns:

```json
{
  "access_token": "<jwt>",
  "refresh_token": "<opaque>",
  "token_type": "bearer"
}
```

The first registered account becomes `ADMIN`.

Subsequent accounts default to `CUSTOMER`.

## Login

```http
POST /api/v1/auth/login
```

```json
{
  "email": "user@example.com",
  "password": "password"
}
```

## Refresh

```http
POST /api/v1/auth/refresh
```

```json
{
  "refresh_token": "<opaque>"
}
```

Refresh tokens are rotated.

Reusing an already-revoked refresh token revokes the entire token family.

## Current User

```http
GET /api/v1/auth/me
Authorization: Bearer <access_token>
```

---

# Ticket Lifecycle

Ticket statuses:

```text
OPEN
IN_PROGRESS
ON_HOLD
RESOLVED
CLOSED
```

Transitions are controlled by the caller's role.

The backend validates status changes before updating the ticket.

Status changes are audited.

---

# SLA

When a ticket is created, the backend searches for an active SLA policy matching the ticket priority.

Priorities:

```text
P1
P2
P3
P4
```

The matching policy is attached to the ticket.

SLA tracking includes:

```text
first_response_due_at
resolution_due_at
first_responded_at
resolved_at
breached_at
status
```

---

# Idempotency

The following endpoints support an optional:

```http
Idempotency-Key: <unique-key>
```

Supported endpoints:

```text
POST /api/v1/tickets
POST /api/v1/tickets/{ticket_id}/comments
```

Idempotency records are stored in PostgreSQL.

Repeated requests using the same key for the same user and endpoint return the previously stored response.

---

# Pagination

List endpoints use:

```text
page
size
```

Defaults:

```text
page = 1
size = 20
```

Maximum:

```text
size = 100
```

Example:

```text
GET /api/v1/tickets?page=1&size=20
```

Response:

```json
{
  "items": [],
  "total": 0,
  "page": 1,
  "size": 20
}
```

---

# Error Format

API errors use:

```json
{
  "error": {
    "code": "NOT_FOUND",
    "message": "Resource not found",
    "details": {}
  },
  "request_id": "<uuid>"
}
```

Common error codes:

| Code                  | HTTP | Meaning                        |
| --------------------- | ---: | ------------------------------ |
| `VALIDATION_ERROR`    |  422 | Request validation failed      |
| `AUTH_REQUIRED`       |  401 | Authentication required        |
| `AUTH_INVALID`        |  401 | Invalid or expired credentials |
| `REFRESH_TOKEN_REUSE` |  401 | Refresh token reuse detected   |
| `FORBIDDEN`           |  403 | Insufficient permissions       |
| `NOT_FOUND`           |  404 | Resource does not exist        |
| `CONFLICT`            |  409 | Resource/state conflict        |
| `RATE_LIMITED`        |  429 | Rate limit exceeded            |
| `INTERNAL_ERROR`      |  500 | Unhandled server error         |

---

# Database

PostgreSQL is the sole persistence and infrastructure dependency.

The backend uses:

```text
SQLAlchemy 2
asyncpg
```

Connection format:

```text
postgresql+asyncpg://USER:PASSWORD@HOST:PORT/DATABASE
```

Current development database:

```text
Host:     192.168.1.38
Port:     5432
Database: ticketing_db
User:     naman
```

Tables are created automatically at application startup.

There is intentionally no Alembic migration layer.

---

# Security

## Passwords

Passwords are never stored in plaintext.

They are hashed using Argon2 through `pwdlib`.

## Access Tokens

Access tokens are JWTs.

They contain:

```text
sub
role
type
exp
```

## Refresh Tokens

Refresh tokens are opaque random values.

Only their hashes are persisted in PostgreSQL.

Refresh-token rotation is enforced.

Refresh-token reuse revokes the complete token family.

## Secrets

Never commit:

```text
.env
```

to Git.

Use:

```text
.env.example
```

for configuration documentation and placeholders.

---

# Development Commands

## Backend

Activate environment:

```cmd
cd backend
.venv\Scripts\activate.bat
```

Run:

```cmd
python -m uvicorn app.main:app --reload --port 8000
```

Install dependencies:

```cmd
python -m pip install -r requirements.txt
```

## Frontend

```cmd
cd frontend
npm install
npm run dev
```

---

# Production Considerations

Before production deployment:

* Use a production-grade PostgreSQL instance.
* Use a strong randomly generated `JWT_SECRET_KEY`.
* Store secrets in environment variables or a secrets manager.
* Do not expose PostgreSQL directly to the public internet.
* Restrict PostgreSQL access to trusted application hosts.
* Use HTTPS.
* Configure CORS explicitly for production frontend origins.
* Run FastAPI behind a production reverse proxy.
* Use a process manager/container orchestration strategy appropriate for deployment.
* Establish a real database migration strategy before making schema changes in production.

The current automatic `create_all()` approach is intended for the current development architecture and deliberately replaces Alembic because this project currently requires PostgreSQL-only infrastructure with no migration service.

---

# Current Development URLs

```text
Frontend
http://localhost:3000

Backend
http://localhost:8000

Swagger
http://localhost:8000/docs

OpenAPI
http://localhost:8000/openapi.json

PostgreSQL
192.168.1.38:5432
```
