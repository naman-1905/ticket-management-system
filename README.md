# Ticket Management System

FastAPI backend for ticket management with PostgreSQL, Redis, RabbitMQ, JWT authentication, role-based access control, SLA support, audit logging, and OpenAPI documentation.

## Requirements

- Python 3.12+
- Docker Desktop and Docker Compose for the full local stack
- Git

## Run with Docker Compose

From the repository root:

```powershell
Copy-Item .env.example .env
docker compose up --build
```

The API is available at http://localhost:8001, Swagger UI at http://localhost:8001/docs, ReDoc at http://localhost:8001/redoc, and RabbitMQ management at http://localhost:15672 (`guest` / `guest`).

The stack starts PostgreSQL, Redis, RabbitMQ, and the API. In development mode, the API creates its SQLAlchemy tables during startup. Stop it with `docker compose down`.

## Run the API locally

Start the backing services:

```powershell
docker compose up -d postgres redis rabbitmq
```

Create and activate a virtual environment from the repository root:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install all runtime and development dependencies:

```powershell
python -m pip install --upgrade pip
python -m pip install -r backend\requirements-dev.txt
```

Create the environment file:

```powershell
Copy-Item .env.example .env
```

For a locally running API, set `POSTGRES_HOST=localhost`, `REDIS_URL=redis://localhost:6379/0`, and `RABBITMQ_URL=amqp://guest:guest@localhost:5672/` in `.env`.

Run Uvicorn:

```powershell
Set-Location backend
..\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8001
```

Open http://127.0.0.1:8001/docs.

## First API request

Register a customer account through Swagger UI or PowerShell:

```powershell
$body = @{ email = "customer@example.com"; full_name = "Example Customer"; password = "change-me-123" } | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8001/api/v1/auth/register -ContentType "application/json" -Body $body
```

Use the returned bearer token with Swagger UI's `Authorize` button. Mutating ticket and comment requests may include an `Idempotency-Key` header.

## Health checks

```powershell
Invoke-RestMethod http://127.0.0.1:8001/healthz
Invoke-RestMethod http://127.0.0.1:8001/health/db
```

`/healthz` reports API liveness and PostgreSQL reachability. A `db: down` response means the API is running but PostgreSQL is unavailable or its environment variables are incorrect.

## Tests and quality checks

```powershell
.\.venv\Scripts\Activate.ps1
pytest -q
pytest --cov=backend/app
ruff check backend/app
mypy backend/app
```

## Project layout

The application lives under `backend/app`: `core` contains settings, security, logging, errors, and idempotency; `db` contains async SQLAlchemy setup; and `modules` contains identity, ticketing, SLA, audit, and notification domains.

## Configuration

Settings are loaded from environment variables using `pydantic-settings`. See [.env.example](.env.example) for the complete reference. Do not use the example JWT secret outside local development.
