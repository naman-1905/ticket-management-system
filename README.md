# Ticket Management System

Full-stack ticket management system with a FastAPI backend and a JavaScript Next.js frontend. Includes PostgreSQL, Redis, RabbitMQ, JWT authentication, role-based access control, SLA support, audit logging, and OpenAPI documentation.

## Requirements

- Python 3.12+
- Docker Desktop and Docker Compose for the full local stack
- Git
- Node.js 22+ (for local frontend development)

## Run with Docker Compose

From the repository root:

```powershell
Copy-Item .env.example .env
docker compose --profile local up --build
```

On Linux/macOS, or from Git Bash/WSL on Windows, the same stack can be started with the repository helper:

```bash
./start.sh
```

The script creates `.env` from `.env.example` when needed, ensures the shared Docker network exists, and starts the frontend and backend dependencies together. Press `Ctrl+C` to stop the foreground Compose stack; use `docker compose down` to remove its containers.

The frontend is available at http://localhost:3000, the API at http://localhost:8000, Swagger UI at http://localhost:8000/docs, ReDoc at http://localhost:8000/redoc, and RabbitMQ management at http://localhost:15672 (`guest` / `guest`).

The stack starts PostgreSQL, Redis, RabbitMQ, and the API. In development mode, the API creates its SQLAlchemy tables during startup. Stop it with `docker compose down`.

The `frontend` service builds a standalone Next.js container and connects to the API using `NEXT_PUBLIC_API_URL`. For local Compose use the default; for a deployed server set it to the public backend URL (for example `http://192.168.1.38:8000/api/v1`) before building.

## Run the frontend locally

```powershell
Set-Location frontend
Copy-Item .env.example .env.local
npm install
npm run dev
```

The frontend uses JavaScript only. Registering a new account creates a customer; agents and administrators can be promoted through the backend role endpoint or the admin Settings page.

For deployment on a server that already provides PostgreSQL, Redis, and RabbitMQ, do not start the local infrastructure profile. Set `POSTGRES_HOST`, `REDIS_URL`, `RABBITMQ_URL`, and the credentials/secrets in `.env`, then run `docker compose up -d --build api`. The Jenkins pipeline applies `alembic upgrade head` before recreating the API container.

## Run the API locally

Start the backing services:

```powershell
docker compose --profile local up -d postgres redis rabbitmq
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

Production must use `ENVIRONMENT=production` and a randomly generated `JWT_SECRET` of at least 32 characters. Secrets are read only from environment variables; `.env` is intentionally ignored by Git.

Run Uvicorn:

```powershell
Set-Location backend
..\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000/docs.

## First API request

Register a customer account through Swagger UI or PowerShell:

```powershell
$body = @{ email = "customer@example.com"; full_name = "Example Customer"; password = "change-me-123" } | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/v1/auth/register -ContentType "application/json" -Body $body
```

Use the returned bearer token with Swagger UI's `Authorize` button. Mutating ticket and comment requests may include an `Idempotency-Key` header.

## Health checks

```powershell
Invoke-RestMethod http://127.0.0.1:8000/healthz
Invoke-RestMethod http://127.0.0.1:8000/health/db
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

The backend lives under `backend/app`: `core` contains settings, security, logging, errors, and idempotency; `db` contains async SQLAlchemy setup; and `modules` contains identity, ticketing, SLA, audit, and notification domains. The frontend lives under `frontend/app` and `frontend/components`, with the API integration in `frontend/lib/api.js`.

## Jenkins deployment

The Jenkinsfile has a `PIPELINE_TARGET` choice parameter: `frontend`, `backend`, or `both`. Backend deployments run migrations and health checks; frontend deployments build and recreate only `ticketing-frontend`. The server must have the repository checked out, Docker Compose installed, and the Jenkins credential `Ticket-Backend-Env` available. Ensure that the backend `CORS_ORIGINS` includes the frontend origin.

## Configuration

Settings are loaded from environment variables using `pydantic-settings`. See [.env.example](.env.example) for the complete reference. Do not use the example JWT secret outside local development.
