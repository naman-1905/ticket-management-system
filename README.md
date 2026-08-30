# Ticket Management System — Backend API Reference

FastAPI backend. All module routers are mounted under `/api/v1`. Interactive docs: `GET /docs` (Swagger UI) and `GET /openapi.json`.

## Conventions

- **Base URL:** `http://localhost:<port>/api/v1`
- **Auth:** Bearer JWT access token in the header — `Authorization: Bearer <access_token>` (obtained from `/auth/login` or `/auth/register`). Roles: `CUSTOMER`, `AGENT`, `ADMIN`.
- **Idempotency:** `POST /tickets` and `POST /tickets/{id}/comments` accept an optional `Idempotency-Key` header; replays return the cached response.
- **Pagination:** list endpoints use query params `page` (≥1, default 1) and `size` (1–100, default 20), returning `{ items, total, page, size }`.

### Error format (all errors)

```json
{
  "error": { "code": "NOT_FOUND", "message": "Resource not found", "details": {} },
  "request_id": "<uuid>"
}
```

| Code | HTTP status | Meaning |
|---|---|---|
| `VALIDATION_ERROR` | 422 | Request validation failed (`details.fields` = pydantic errors) |
| `AUTH_REQUIRED` / `AUTH_INVALID` | 401 | Missing/invalid/expired token, bad credentials |
| `REFRESH_TOKEN_REUSE` | 401 | Refresh-token reuse detected (whole family revoked) |
| `FORBIDDEN` | 403 | Insufficient role or resource not owned by user |
| `NOT_FOUND` | 404 | Resource does not exist |
| `CONFLICT` | 409 | Duplicate email, last-admin demotion blocked, etc. |
| `RATE_LIMITED` | 429 | Too many login attempts from the client IP |
| `INTERNAL_ERROR` | 500 | Unhandled server error |

---

## Root & Health (no auth)

### `GET /`
Service banner. → `{"message": "Ticket Management System Backend is running"}`

### `GET /healthz` · `GET /health`
→ `{"status": "ok", "db": "up|down"}`

### `GET /health/db`
→ `{"status": "healthy" | "unhealthy"}`

### `GET /api/v1/meta/version`
→ `{"version": "<app_version>", "git_sha": "unknown"}`

---

## Auth — `/api/v1/auth` (tag: `auth`)

### `POST /api/v1/auth/register` → 201
Create an account; returns a token pair. Rate-limited per IP like login.

**Body:**
```json
{ "email": "user@example.com", "full_name": "Jane Doe", "password": "min-8-chars" }
```
(`full_name` 1–200 chars, `password` ≥ 8 chars)

**Response (TokenOut):**
```json
{ "access_token": "<jwt>", "refresh_token": "<opaque>", "token_type": "bearer" }
```
Errors: `409 CONFLICT` email already registered.

### `POST /api/v1/auth/login` → 200
**Body:** `{ "email": "...", "password": "..." }`
**Response (TokenOut):** as above.
Errors: `401 AUTH_INVALID`, `429 RATE_LIMITED`.

### `POST /api/v1/auth/refresh` → 200
Rotate the refresh token (old one revoked; reuse revokes the whole family).
**Body:** `{ "refresh_token": "<opaque>" }`
**Response (TokenOut):** as above. Errors: `401 AUTH_REQUIRED`, `401 REFRESH_TOKEN_REUSE`.

### `POST /api/v1/auth/logout` → 204
Requires Bearer token. Revokes the given refresh token for the current user.
**Body:** `{ "refresh_token": "<opaque>" }` — no response body.

### `GET /api/v1/auth/me` → 200
Requires Bearer token (any role). Returns the current user.
**Response (UserOut):**
```json
{ "id": "<uuid>", "email": "...", "full_name": "...", "role": "CUSTOMER|AGENT|ADMIN", "is_active": true }
```

---

## Users — `/api/v1/users` (tag: `users`)

### `GET /api/v1/users` → 200
Requires role **AGENT or ADMIN**. Lists users ordered by email.
**Query:** `role` (optional, filter by `CUSTOMER|AGENT|ADMIN`).
**Response:** array of full user rows (DB model):
```json
[ { "id": "<uuid>", "email": "...", "full_name": "...", "password_hash": "...", "role": "...", "is_active": true, "created_at": "<iso8601>" } ]
```

### `PATCH /api/v1/users/{user_id}/role` → 200
Requires role **ADMIN**. Change a user's role.
**Path:** `user_id` (UUID). **Body:** `{ "role": "CUSTOMER|AGENT|ADMIN" }`
**Response:** updated full user row (as above).
Errors: `404 NOT_FOUND`, `409 CONFLICT` ("Cannot demote the last active administrator").

---

## Tickets — `/api/v1/tickets` (tag: `tickets`)

All endpoints require a Bearer token. Customers only see their own tickets (`customer_id == user.id`).

### `POST /api/v1/tickets` → 201
Create a ticket (any role; `customer_id`/`created_by` = caller). An active SLA policy matching the priority is attached automatically, and a `ticket.created` event is published.
**Header:** optional `Idempotency-Key`.
**Body (TicketCreate):**
```json
{ "title": "...", "description": "...", "priority": "P1|P2|P3|P4", "category": "optional, ≤50 chars" }
```
(`title` 1–300, `description` ≥ 1 char, `priority` default `"P3"`)

**Response (TicketOut):**
```json
{
  "id": "<uuid>", "ticket_number": "TCK-<12 hex uppercase>",
  "title": "...", "description": "...",
  "status": "OPEN|IN_PROGRESS|ON_HOLD|RESOLVED|CLOSED",
  "priority": "P3", "category": null,
  "customer_id": "<uuid>", "assignee_id": null,
  "created_at": "<iso8601>"
}
```

### `GET /api/v1/tickets` → 200
List tickets (newest first). Customers are scoped to their own; AGENT/ADMIN may filter by any customer.
**Query:** `page`, `size`, plus optional filters `status`, `priority`, `category`, `customer_id` (UUID), `assignee_id` (UUID).
**Response:** `{ "items": [TicketOut...], "total": 42, "page": 1, "size": 20 }`

### `GET /api/v1/tickets/{ticket_id}` → 200
Fetch one ticket. **Path:** `ticket_id` (UUID).
**Response (TicketOut):** as above. Errors: `404 NOT_FOUND`, `403 FORBIDDEN`.

### `PATCH /api/v1/tickets/{ticket_id}/status` → 200
Change status; validated against the state machine for the caller's role, audited, and a `ticket.status_changed` event is published.
**Body (TicketStatus):** `{ "status": "OPEN|IN_PROGRESS|ON_HOLD|RESOLVED|CLOSED" }`
**Response (TicketOut).** Errors: `403 FORBIDDEN`, `404 NOT_FOUND`.

### `POST /api/v1/tickets/{ticket_id}/assign` → 200
Requires role **AGENT or ADMIN**. Assign an active agent/admin.
**Body (Assignment):** `{ "assignee_id": "<uuid>" }`
**Response (TicketOut).** Errors: `403 FORBIDDEN`, `404 NOT_FOUND` ("Active agent not found").

### `GET /api/v1/tickets/{ticket_id}/comments` → 200
List comments. Customers only see non-internal ones.
**Response:** array of CommentOut:
```json
[ { "id": "<uuid>", "ticket_id": "<uuid>", "author_id": "<uuid>", "body": "...", "is_internal": false, "created_at": "<iso8601>" } ]
```

### `POST /api/v1/tickets/{ticket_id}/comments` → 201
Add a comment (audited; `comment.added` event published). Customers cannot create internal comments.
**Header:** optional `Idempotency-Key`.
**Body (CommentCreate):** `{ "body": "...", "is_internal": false }`
**Response (CommentOut).** Errors: `403 FORBIDDEN`, `404 NOT_FOUND`.

---

## SLA — tag: `sla`

### `GET /api/v1/sla/policies` → 200
Requires role **AGENT or ADMIN**. Lists active policies.
**Response:** array of SLAPolicy rows:
```json
[ { "id": "<uuid>", "name": "...", "priority": "P1|P2|P3|P4", "first_response_minutes": 30, "resolution_hours": 8, "is_active": true, "created_at": "<iso8601>", "updated_at": "<iso8601>" } ]
```

### `POST /api/v1/sla/policies` → 201
Requires role **ADMIN**. Create a policy.
**Body (SLAPolicyIn):**
```json
{ "name": "...", "priority": "P1|P2|P3|P4", "first_response_minutes": 30, "resolution_hours": 8, "is_active": true }
```
(`name` 1–100 unique, `priority` must match `^P[1-4]$`, both durations > 0)
**Response:** created SLAPolicy row.

### `PATCH /api/v1/sla/policies/{policy_id}` → 200
Requires role **ADMIN**. Full update of a policy (same body as create).
**Path:** `policy_id` (UUID). **Response:** updated SLAPolicy row. Errors: `404 NOT_FOUND`.

### `GET /api/v1/tickets/{ticket_id}/sla` → 200
Requires Bearer token; customers only for their own tickets. Returns the ticket's SLA tracking record, or a pending placeholder if none exists yet.
**Response (TicketSLA row):**
```json
{
  "id": "<uuid>", "ticket_id": "<uuid>", "policy_id": "<uuid>",
  "first_response_due_at": "<iso8601|null>", "resolution_due_at": "<iso8601|null>",
  "first_responded_at": null, "resolved_at": null, "breached_at": null,
  "status": "ACTIVE"
}
```
or `{ "ticket_id": "<uuid>", "status": "PENDING" }` when no SLA row exists.

---

## Audit — `/api/v1/audit` (tag: `audit`)

### `GET /api/v1/audit/logs` → 200
Requires role **ADMIN**. Paginated audit trail, newest first.
**Query:** `page`, `size`, plus optional filters `entity_type` (e.g. `"ticket"`), `entity_id` (UUID), `actor_id` (UUID).
**Response:** `{ "items": [AuditLog...], "total": n, "page": 1, "size": 20 }` where each AuditLog is:
```json
{
  "id": "<uuid>", "actor_id": "<uuid|null>", "action": "ticket.created",
  "entity_type": "ticket", "entity_id": "<uuid|null>",
  "old_values": { }, "new_values": { },
  "correlation_id": null, "created_at": "<iso8601>"
}
```

---

## Endpoint summary

| Method | URL | Auth (roles) | Purpose |
|---|---|---|---|
| GET | `/` | — | Service banner |
| GET | `/healthz`, `/health` | — | Liveness + DB state |
| GET | `/health/db` | — | DB health only |
| GET | `/api/v1/meta/version` | — | App version |
| POST | `/api/v1/auth/register` | — (201) | Create account, get tokens |
| POST | `/api/v1/auth/login` | — | Login, get tokens |
| POST | `/api/v1/auth/refresh` | — | Rotate refresh token |
| POST | `/api/v1/auth/logout` | any (204) | Revoke refresh token |
| GET | `/api/v1/auth/me` | any | Current user profile |
| GET | `/api/v1/users` | AGENT, ADMIN | List users (`?role=`) |
| PATCH | `/api/v1/users/{user_id}/role` | ADMIN | Change a user's role |
| POST | `/api/v1/tickets` | any (201) | Create ticket (+ idempotency key) |
| GET | `/api/v1/tickets` | any | List/filter tickets (paginated) |
| GET | `/api/v1/tickets/{ticket_id}` | any | Get one ticket |
| PATCH | `/api/v1/tickets/{ticket_id}/status` | any | Change status (state machine) |
| POST | `/api/v1/tickets/{ticket_id}/assign` | AGENT, ADMIN | Assign an agent |
| GET | `/api/v1/tickets/{ticket_id}/comments` | any | List comments |
| POST | `/api/v1/tickets/{ticket_id}/comments` | any (201) | Add comment (+ idempotency key) |
| GET | `/api/v1/sla/policies` | AGENT, ADMIN | List active SLA policies |
| POST | `/api/v1/sla/policies` | ADMIN (201) | Create SLA policy |
| PATCH | `/api/v1/sla/policies/{policy_id}` | ADMIN | Update SLA policy |
| GET | `/api/v1/tickets/{ticket_id}/sla` | any | Ticket's SLA tracking record |
| GET | `/api/v1/audit/logs` | ADMIN | Paginated audit log (filters) |
