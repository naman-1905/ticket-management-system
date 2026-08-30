# Ticket Management System Backend

FastAPI + PostgreSQL only.

No Redis, RabbitMQ, Alembic, Celery, or other infrastructure is required.

## Run

1. Create a PostgreSQL database named `ticket_management`.
2. Copy `.env.example` to `.env` and update credentials.
3. Install dependencies:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

4. Start:

```powershell
uvicorn app.main:app --reload --port 8000
```

Tables are created automatically with SQLAlchemy `create_all()` at startup.

Swagger: http://localhost:8000/docs
OpenAPI: http://localhost:8000/openapi.json

## Notes

- Refresh tokens are stored hashed in PostgreSQL and rotated.
- Refresh-token reuse revokes the entire token family.
- Idempotency responses are stored in PostgreSQL.
- Audit records are stored in PostgreSQL.
- Ticket/SLA events are represented by persisted audit records; no message broker is used.
- The first registered user becomes ADMIN. Subsequent registrations become CUSTOMER.
