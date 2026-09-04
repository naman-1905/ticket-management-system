# Ticket Management System

A full-stack service desk platform built with **Next.js** and **FastAPI**, backed by **PostgreSQL**.

## Features

- Multi-tenant organizations with role-based access control
- Ticket lifecycle management with comments, assignments, and attachments
- SLA policies and tracking
- Knowledge base and customer portal
- Audit logging, notifications, search, and reporting
- Background worker for async jobs

## Architecture

```text
┌──────────────────────────────┐
│          Frontend            │
│          Next.js             │
│          :3000               │
└──────────────┬───────────────┘
               │ HTTP/REST
               ▼
┌──────────────────────────────┐
│           Backend            │
│           FastAPI            │
│          :8000               │
└──────────────┬───────────────┘
               │ PostgreSQL
               ▼
┌──────────────────────────────┐
│         PostgreSQL           │
│          :5432               │
└──────────────────────────────┘
```

## Project Structure

```text
ticket-management-system/
├── backend/
│   ├── app/              # FastAPI application
│   ├── alembic/          # Database migrations
│   ├── scripts/          # Bootstrap and maintenance scripts
│   ├── tests/
│   ├── requirements.txt
│   ├── start-backend.sh
│   └── .env.example
├── frontend/
│   ├── app/              # Next.js App Router pages
│   ├── lib/              # API client, auth, permissions
│   ├── start-frontend.sh
│   └── .env.example
├── docker-compose.yml
├── start.bat
├── start.sh
└── README.md
```

## Technology Stack

| Layer    | Technologies |
| -------- | ------------ |
| Frontend | Next.js, React, Tailwind CSS |
| Backend  | FastAPI, SQLAlchemy 2, asyncpg, Pydantic, Alembic |
| Auth     | JWT access tokens, opaque refresh tokens, Argon2 password hashing |
| Database | PostgreSQL |

## Prerequisites

- Python 3.12+
- Node.js 18+
- PostgreSQL 14+

## Quick Start

### 1. Database

Create a PostgreSQL database:

```sql
CREATE DATABASE ticketing_db;
```

### 2. Backend

```bash
cd backend
python -m venv .venv
```

**Windows**

```cmd
.venv\Scripts\activate.bat
```

**Linux / macOS**

```bash
source .venv/bin/activate
```

Install dependencies and configure the environment:

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
cp .env.example .env
```

Edit `backend/.env` with your database credentials and a strong JWT secret:

```env
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/ticketing_db
JWT_SECRET_KEY=your-generated-secret
```

Generate a JWT secret:

```bash
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

Bootstrap the schema:

```bash
python -m scripts.bootstrap_db
```

Start the API:

```bash
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- API: `http://localhost:8000`
- Swagger UI: `http://localhost:8000/docs`
- OpenAPI: `http://localhost:8000/openapi.json`

### 3. Frontend

```bash
cd frontend
npm install
cp .env.example .env.local
```

Set the API URL in `frontend/.env.local`:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
```

Start the dev server:

```bash
npm run dev
```

Frontend: `http://localhost:3000`

### 4. Start Both (optional)

From the project root:

```cmd
start.bat
```

```bash
chmod +x start.sh && ./start.sh
```

Or run each service in its own terminal:

```bash
./backend/start-backend.sh    # FastAPI on :8000
./frontend/start-frontend.sh  # Next.js on :3000
```

## Frontend Pages

| Route | Description |
| ----- | ----------- |
| `/login`, `/register` | Authentication |
| `/dashboard` | Staff overview |
| `/tickets`, `/tickets/new`, `/tickets/[id]` | Ticket management |
| `/sla` | SLA policy management |
| `/customers` | Organization management |
| `/admin/users` | User and role management |
| `/admin/audit` | Audit log viewer |
| `/portal/tickets` | Customer ticket portal |
| `/portal/kb` | Customer knowledge base |

## API Overview

All versioned routes are under `/api/v1`.

| Area | Prefix |
| ---- | ------ |
| Auth | `/api/v1/auth` |
| Users | `/api/v1/users` |
| Tickets | `/api/v1/tickets` |
| SLA | `/api/v1/sla` |
| Audit | `/api/v1/audit` |
| Organizations | `/api/v1/organizations` |
| Contacts | `/api/v1/contacts` |
| Teams | `/api/v1/teams` |
| Notifications | `/api/v1/notifications` |
| Search | `/api/v1/search` |
| Reports | `/api/v1/reports` |
| Knowledge base | `/api/v1/kb` |
| CSAT | `/api/v1/csat` |
| Attachments | `/api/v1/attachments` |
| Automations | `/api/v1/automations` |

See [backend/README.md](backend/README.md) for detailed endpoint documentation.

### Authentication

Requests use a Bearer token:

```text
Authorization: Bearer <access_token>
```

Register or log in to receive an access/refresh token pair. The first registered account in a tenant becomes an administrator.

### Pagination

List endpoints accept `page` (default `1`) and `size` (default `20`, max `100`).

### Idempotency

`POST /api/v1/tickets` and `POST /api/v1/tickets/{id}/comments` accept an optional `Idempotency-Key` header.

## Environment Variables

### Backend (`backend/.env`)

| Variable | Description |
| -------- | ----------- |
| `DATABASE_URL` | PostgreSQL connection string |
| `JWT_SECRET_KEY` | Secret for signing access tokens |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Access token lifetime (default `30`) |
| `REFRESH_TOKEN_EXPIRE_DAYS` | Refresh token lifetime (default `30`) |
| `CORS_ORIGINS` | Comma-separated allowed origins |
| `DOCS_ENABLED` | Enable Swagger UI (`true`/`false`) |
| `STORAGE_DIR` | Local file storage path |
| `WORKER_POLL_SECONDS` | Background worker poll interval |

### Frontend (`frontend/.env.local`)

| Variable | Description |
| -------- | ----------- |
| `NEXT_PUBLIC_API_URL` | Backend API base URL |

## Development

### Run backend tests

```bash
cd backend
pytest
```

### Database migrations

```bash
cd backend
alembic upgrade head
```

## Docker

The project includes a `docker-compose.yml` for containerized deployment. Configure a `.env` file at the project root before running:

```bash
docker compose up -d
```

## Security Notes

- Never commit `.env` files or secrets to source control.
- Use a strong, randomly generated `JWT_SECRET_KEY` in production.
- Restrict PostgreSQL access to trusted application hosts.
- Use HTTPS and configure CORS for production frontend origins.

## License

Private project — all rights reserved.
