# Ticket Management System — Comprehensive Project Summary

A full-stack **service desk / IT ticketing platform** for multi-tenant organizations. Staff manage support tickets, SLAs, customers, and teams; customers use a self-service portal. Built with **Next.js** (frontend), **FastAPI** (backend), and **PostgreSQL** (database).

---

## Table of Contents

1. [High-Level Architecture](#1-high-level-architecture)
2. [Technology Stack](#2-technology-stack)
3. [Project Structure](#3-project-structure)
4. [Multi-Tenancy & Security Model](#4-multi-tenancy--security-model)
5. [Backend — Detailed Functionality](#5-backend--detailed-functionality)
6. [Frontend — Detailed Functionality](#6-frontend--detailed-functionality)
7. [Data Model](#7-data-model)
8. [Background Worker & Async Jobs](#8-background-worker--async-jobs)
9. [DevOps & Deployment](#9-devops--deployment)
10. [API Conventions](#10-api-conventions)
11. [End-to-End Flows](#11-end-to-end-flows)
12. [Gaps & Backend-Only Features](#12-gaps--backend-only-features)

---

## 1. High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Frontend (Next.js)                       │
│                     Port 3000                                │
│  - Staff UI: dashboard, tickets, SLA, admin                  │
│  - Customer portal: my tickets, knowledge base               │
└──────────────────────────┬──────────────────────────────────┘
                           │ HTTP/REST (JSON)
                           │ Bearer JWT + optional Idempotency-Key
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                     Backend (FastAPI)                        │
│                     Port 8000                                │
│  - REST API under /api/v1                                    │
│  - Auth, RBAC, ticket lifecycle, SLA, audit, etc.            │
└──────────────────────────┬──────────────────────────────────┘
                           │ asyncpg (SQLAlchemy 2 async)
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                     PostgreSQL                               │
│                     Port 5432                                │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│              Background Worker (separate process)            │
│  - SLA breach detection                                      │
│  - Job queue processing                                      │
│  - Heartbeat for /readyz health check                        │
└─────────────────────────────────────────────────────────────┘
```

**Request lifecycle (simplified):**

1. Frontend sends request with `Authorization: Bearer <access_token>`.
2. Middleware assigns a unique `request_id` (returned as `X-Request-ID`).
3. `current_user` dependency decodes JWT, loads user, validates tenant.
4. Route handler checks permissions via `require_permissions` or inline checks.
5. Business logic runs in service layer; audit events are recorded.
6. JSON response returned; errors use a standardized envelope.

---

## 2. Technology Stack

| Layer | Technologies |
|-------|-------------|
| **Frontend** | Next.js 16 (App Router), React 19, Tailwind CSS 4, Framer Motion, Lucide icons |
| **Backend** | FastAPI, SQLAlchemy 2 (async), asyncpg, Pydantic v2, Alembic |
| **Auth** | JWT access tokens (HS256), opaque refresh tokens (SHA-256 hashed), Argon2 password hashing via `pwdlib` |
| **Database** | PostgreSQL 14+ |
| **Storage** | Local filesystem for attachments (`STORAGE_DIR`) |
| **CI/CD** | Jenkins pipeline, Docker Compose |
| **Testing** | pytest, pytest-asyncio, httpx |

---

## 3. Project Structure

```
ticket-management-system/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app, middleware, router mounting
│   │   ├── config.py            # Environment settings (Pydantic Settings)
│   │   ├── db.py                # Async engine & session factory
│   │   ├── deps.py              # Auth dependencies (current_user, require_permissions)
│   │   ├── security.py          # Password hashing, JWT, refresh token management
│   │   ├── schemas.py           # Pydantic request/response models
│   │   ├── models/__init__.py   # SQLAlchemy ORM models (all entities)
│   │   ├── routers/             # API route modules (auth, tickets, sla, etc.)
│   │   ├── services/            # Business logic (tickets, tenancy, sla, audit, idempotency)
│   │   ├── domain/              # Domain rules (ticket lifecycle state machine)
│   │   ├── core/                # Permissions catalog, errors, logging
│   │   ├── storage/             # Local file storage for attachments
│   │   └── jobs/worker.py       # Background worker process
│   ├── alembic/                 # Database migrations
│   ├── scripts/                 # bootstrap_db.py, reset_db.py
│   └── tests/                   # Unit and API tests
├── frontend/
│   ├── app/                     # Next.js App Router pages & components
│   ├── lib/                     # api.js, auth-context, permissions, theme, format
│   └── package.json
├── docker-compose.yml           # ticket-be, ticket-worker, ticket-fe
├── Jenkinsfile                  # Build & deploy pipeline
├── start.sh / start.bat         # Local dev: run both services
└── README.md
```

---

## 4. Multi-Tenancy & Security Model

### 4.1 Tenants

- Each **organization** that registers gets a `Tenant` record (name, slug, timezone, plan, features).
- All data (tickets, users, SLA policies, etc.) is scoped by `tenant_id`.
- Registration creates: tenant → default roles/permissions → owner user → internal organization → contact linked to user → default SLA policies.

### 4.2 Roles

| Role | User Type | Purpose |
|------|-----------|---------|
| **OWNER** | staff | Full permissions; first registrant gets this role |
| **ADMIN** | staff | Nearly full access (no `sla.override`) |
| **SUPERVISOR** | staff | Team/queue management, reports, audit, SLA override |
| **AGENT** | staff | Ticket handling, comments, KB management |
| **CUSTOMER** | customer | Own tickets, public comments, KB view |
| **CUSTOMER_ADMIN** | customer | Customer role + contact management |

Legacy mapping: `ADMIN` → ADMIN, `AGENT` → AGENT, `CUSTOMER` → CUSTOMER.

### 4.3 Permission System

Granular permissions (30 total) include:

- **Tickets:** `ticket.view`, `ticket.view_own`, `ticket.create`, `ticket.update`, `ticket.assign`, `ticket.delete`, `ticket.merge`, `ticket.escalate`, `ticket.transition`
- **Comments:** `comment.public.write`, `comment.internal.read`, `comment.internal.write`
- **SLA:** `sla.view`, `sla.manage`, `sla.override`
- **Admin:** `user.manage`, `team.manage`, `queue.manage`, `organization.manage`, `contact.manage`, `automation.manage`, `audit.view`, `settings.manage`
- **Other:** `report.view`, `report.export`, `kb.manage`, `kb.view`, `notification.manage`

Permissions are stored in DB (`permissions`, `roles`, `role_permissions`, `user_roles`) and seeded on registration. The `User.role` field is kept for backward compatibility; effective permissions come from `UserRole` joins, with fallback to `DEFAULT_ROLES` mapping.

### 4.4 Authentication

| Mechanism | Details |
|-----------|---------|
| **Access token** | JWT, 30 min default, payload: `sub`, `role`, `tenant_id`, `type: access` |
| **Refresh token** | Opaque 48-byte URL-safe token, stored as SHA-256 hash |
| **Token rotation** | Refresh endpoint revokes old token and issues new pair |
| **Reuse detection** | If a revoked refresh token is reused, entire token family is revoked |
| **Rate limiting** | 20 login/register attempts per minute per IP/email (in-memory) |
| **Password** | Argon2 via `pwdlib`, minimum 8 characters |

### 4.5 Authorization Patterns

- **`current_user`**: Any authenticated active user.
- **`require_permissions("x", "y")`**: User must have all listed permissions (or be platform admin).
- **`require_roles(...)`**: Legacy role check (less used; permissions preferred).
- **Resource scoping**: Tickets filtered by `tenant_id`; customers see only own tickets via `ticket.view_own`.

---

## 5. Backend — Detailed Functionality

All versioned routes are under `/api/v1`. Interactive docs at `/docs` when `DOCS_ENABLED=true`.

### 5.1 Health & Meta (No Auth)

| Endpoint | Purpose |
|----------|---------|
| `GET /` | Service banner message |
| `GET /healthz`, `GET /health` | Liveness + DB connectivity (`db: up\|down`) |
| `GET /readyz` | Readiness: DB up + worker heartbeat within 5 minutes |
| `GET /health/db` | DB-only health check |
| `GET /api/v1/meta/version` | App version and git SHA |

### 5.2 Authentication (`/api/v1/auth`)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/register` | POST | Create tenant + owner account. Body: `email`, `full_name`, `password`, `tenant_name`. Returns token pair. Seeds permissions, roles, default SLAs. Rate-limited. |
| `/login` | POST | Authenticate with email/password. Returns token pair. Rate-limited per IP. |
| `/refresh` | POST | Rotate refresh token. Detects reuse and revokes family. |
| `/logout` | POST | Revokes refresh token family. Requires Bearer token. |
| `/me` | GET | Current user profile with `permissions[]`, `tenant_name`, `user_type`. |

**How registration works:**
1. Check email not already registered (409 if duplicate).
2. `seed_permissions()` ensures all permission codes exist globally.
3. `create_tenant_with_owner()` creates tenant, seeds tenant roles, creates OWNER user (staff), internal org, and contact.
4. `ensure_default_sla_policies()` creates P1–P4 default policies.
5. Issue tokens, audit `auth.register`, commit.

### 5.3 Users (`/api/v1/users`)

| Endpoint | Permission | Description |
|----------|------------|-------------|
| `GET /users` | `user.manage` | List all users in tenant. Optional `?role=` filter. |
| `GET /users/agents` | `ticket.assign` | List active staff users (for assignment dropdowns). |
| `PATCH /users/{id}/role` | `user.manage` | Change user role. Re-syncs `UserRole` records. Blocks demoting last OWNER. Audited. |

### 5.4 Tickets (`/api/v1/tickets`)

Core of the platform. All endpoints require authentication.

#### Create Ticket — `POST /tickets`

- **Permission:** `ticket.create`
- **Idempotency:** Optional `Idempotency-Key` header
- **Body:** `title`, `description`, `priority` (P1–P4, default P3), `category`, `ticket_type` (default INCIDENT), `source` (default WEB), `organization_id`, `requester_contact_id`
- **Behavior:**
  1. Generates ticket number: `TCK-000001` format (sequential per tenant).
  2. Sets status to `NEW`.
  3. Links customer via user or contact record.
  4. Builds `search_vector` for full-text-style search.
  5. Attaches matching SLA policy by priority.
  6. Audits `ticket.created`.
  7. Caches response if idempotency key provided.

#### List Tickets — `GET /tickets`

- **Permission:** `ticket.view` (all tenant tickets) or `ticket.view_own` (scoped to customer)
- **Pagination:** `page` (default 1), `size` (1–100, default 20)
- **Filters:** `status`, `priority`, `category`, `assignee_id`, `q` (search)
- **Response:** `{ items: TicketOut[], total, page, size }`
- Each `TicketOut` includes `allowed_transitions[]` based on user role and current status.

#### Get Ticket — `GET /tickets/{id}`

- Returns single ticket with allowed transitions.
- 404 if not found or not accessible (customers can't see others' tickets).

#### Status Transitions

Two endpoints (legacy + new):

| Endpoint | Body | Notes |
|----------|------|-------|
| `POST /tickets/{id}/transitions` | `{ to_status, version? }` | Preferred. Optimistic locking via `version`. |
| `PATCH /tickets/{id}/status` | `{ status }` | Legacy compatibility. |

**State machine** (`domain/ticket_lifecycle.py`):

Statuses: `NEW`, `OPEN`, `IN_PROGRESS`, `WAITING_FOR_CUSTOMER`, `WAITING_FOR_INTERNAL`, `ON_HOLD`, `RESOLVED`, `CLOSED`, `CANCELLED`.

Role-specific allowed transitions:
- **CUSTOMER:** NEW→OPEN/CANCELLED, OPEN→CANCELLED, RESOLVED→CLOSED
- **AGENT/SUPERVISOR:** Full workflow minus some admin-only paths
- **ADMIN/OWNER:** All transitions including reopening CLOSED tickets

**On transition:**
- Validates permission (`ticket.transition` or customer `ticket.view_own` + valid transition).
- Updates `version`, timestamps (`resolved_at`, `closed_at`).
- **SLA pause/resume:** ON_HOLD, WAITING_FOR_* statuses pause SLA timers; resuming extends due dates by paused duration.
- On RESOLVED: marks SLA resolved, status MET or BREACHED.
- Audits `ticket.status_changed` with correlation ID.

#### Assign Ticket — `POST /tickets/{id}/assign`

- **Permission:** `ticket.assign`
- **Body:** `assignee_id`, `team_id`, `queue_id` (all optional)
- Validates assignee is active staff in same tenant.
- Increments ticket `version`.

#### Comments

| Endpoint | Description |
|----------|-------------|
| `GET /tickets/{id}/comments` | List comments. Customers see only non-internal (`is_internal=false`). |
| `POST /tickets/{id}/comments` | Add comment. Body: `body`, `is_internal`. Idempotency supported. |

**On public comment:**
- Sets `ticket.first_response_at` if first public reply.
- Updates SLA `first_responded_at`; records `first_response_met` SLA event if within deadline.
- Updates ticket `search_vector`.
- Audits `comment.added`.

#### Bulk Actions — `POST /tickets/bulk`

- **Permission:** `ticket.update`
- **Body:** `{ ticket_ids[], action, payload }`
- Actions: `assign` (set assignee_id), `status` (transition), `priority` (change priority)
- Returns `{ updated, errors[] }` per-ticket error handling.

### 5.5 SLA (`/api/v1/sla`)

| Endpoint | Permission | Description |
|----------|------------|-------------|
| `GET /sla/policies` | `sla.view` | List active policies ordered by priority |
| `POST /sla/policies` | `sla.manage` | Create policy + version 1 snapshot |
| `PATCH /sla/policies/{id}` | `sla.manage` | Update policy, append new version |
| `GET /tickets/{id}/sla` | authenticated | Ticket SLA tracking record or `{ status: "PENDING" }` |

**SLA attachment (on ticket create):**
- Finds active policy matching ticket priority.
- Creates `TicketSLA` with `first_response_due_at` and `resolution_due_at`.
- Records `sla_started` event.

**Default policies (on tenant creation):**

| Priority | Name | First Response | Resolution |
|----------|------|----------------|------------|
| P1 | P1 Critical | 15 min | 4 hours |
| P2 | P2 High | 30 min | 8 hours |
| P3 | P3 Normal | 60 min | 24 hours |
| P4 | P4 Low | 240 min | 72 hours |

**SLA statuses:** `ACTIVE`, `MET`, `BREACHED`, `PENDING` (no SLA row yet).

### 5.6 Organizations (`/api/v1/organizations`)

| Endpoint | Permission | Description |
|----------|------------|-------------|
| `GET /organizations` | `organization.manage` | List customer organizations |
| `POST /organizations` | `organization.manage` | Create org. Body: `name`, `org_type` (default "customer"). Unique per tenant. |

### 5.7 Contacts (`/api/v1/contacts`)

| Endpoint | Permission | Description |
|----------|------------|-------------|
| `GET /contacts` | `contact.manage` | List contacts |
| `POST /contacts` | `contact.manage` | Create contact. Body: `email`, `full_name`, `organization_id?`. Unique email per tenant. |

### 5.8 Teams & Queues (`/api/v1/teams`, `/api/v1/queues`)

| Endpoint | Permission | Description |
|----------|------------|-------------|
| `GET /teams` | `team.manage` | List teams |
| `POST /teams` | `team.manage` | Create team |
| `POST /teams/{id}/members/{user_id}` | `team.manage` | Add team member |
| `GET /queues` | `queue.manage` | List queues |
| `POST /queues` | `queue.manage` | Create queue. Body: `name`, `team_id?`, `assignment_mode` (default "manual") |

### 5.9 Notifications (`/api/v1/notifications`)

| Endpoint | Description |
|----------|-------------|
| `GET /notifications` | Last 50 in-app notifications for current user |
| `POST /notifications/read-all` | Mark all as read |

Notifications are created by the worker on SLA breach (to assignee).

### 5.10 Search (`/api/v1/search`)

| Endpoint | Permission | Description |
|----------|------------|-------------|
| `GET /search/tickets?q=` | `ticket.view` | Search tickets by `search_vector`, ticket_number, title. Paginated. |

### 5.11 Reports (`/api/v1/reports`)

| Endpoint | Permission | Description |
|----------|------------|-------------|
| `GET /reports/tickets/summary` | `report.view` | Dashboard metrics: `open_tickets`, `resolved_tickets`, `unassigned`, `sla_breached` |

Open statuses counted: NEW, OPEN, IN_PROGRESS, WAITING_FOR_CUSTOMER, WAITING_FOR_INTERNAL, ON_HOLD.

### 5.12 Knowledge Base (`/api/v1/kb`)

| Endpoint | Permission | Description |
|----------|------------|-------------|
| `GET /kb/articles` | authenticated | Staff see all; customers see only `visibility=public` + `status=published` |
| `POST /kb/articles` | `kb.manage` | Create article. Body: `title`, `body`, `visibility`, `status` |
| `GET /kb/articles/{id}` | authenticated | Get single article (visibility enforced) |

### 5.13 CSAT (`/api/v1/csat`)

| Endpoint | Description |
|----------|-------------|
| `POST /csat/tickets/{id}` | Submit satisfaction rating. Body: `score` (1–5), `comment?`. Only for RESOLVED/CLOSED tickets. One rating per ticket. |

### 5.14 Attachments (`/api/v1/attachments`)

| Endpoint | Description |
|----------|-------------|
| `POST /attachments/tickets/{id}` | Upload file (multipart). Max 10 MB. Stored locally with SHA-256 checksum. |
| `GET /attachments/tickets/{id}` | List attachments for ticket |

Storage path: `{STORAGE_DIR}/{tenant_id}/{uuid}_{filename}`.

### 5.15 Automations & Productivity (`/api/v1`)

| Endpoint | Permission | Description |
|----------|------------|-------------|
| `GET /rules` | `automation.manage` | List automation rules |
| `POST /rules` | `automation.manage` | Create rule. Body: `name`, `trigger_event`, `conditions`, `actions`, `sort_order`, `is_active` |
| `GET /saved-views` | authenticated | User's views + shared views |
| `POST /saved-views` | authenticated | Create saved filter view |
| `GET /macros` | authenticated | List active reply macros |
| `POST /macros` | authenticated | Create macro |
| `GET /tags` | authenticated | List tags |
| `POST /tags` | authenticated | Create tag |
| `POST /tickets/{id}/tags/{tag_id}` | authenticated | Tag a ticket |

> **Note:** Automation rules are stored but rule execution engine is not wired to ticket events in the current codebase.

### 5.16 Audit (`/api/v1/audit`)

| Endpoint | Permission | Description |
|----------|------------|-------------|
| `GET /audit/logs` | `audit.view` | Paginated audit trail. Filters: `entity_type`, `entity_id`, `actor_id`. Enriched with actor/entity names. |

**Audited actions include:** `auth.register`, `auth.login`, `auth.logout`, `ticket.created`, `ticket.status_changed`, `comment.added`, `user.role_changed`, `organization.created`, `contact.created`, `sla.policy_created`, `sla.policy_updated`.

### 5.17 Idempotency

Supported on:
- `POST /tickets`
- `POST /tickets/{id}/comments`

Client sends `Idempotency-Key` header. Server stores `(user_id, endpoint, key) → response_body`. Replays return cached response without re-executing.

### 5.18 Error Handling

All errors return:

```json
{
  "error": { "code": "NOT_FOUND", "message": "...", "details": {} },
  "request_id": "<uuid>"
}
```

| Code | HTTP | Meaning |
|------|------|---------|
| `VALIDATION_ERROR` | 422 | Pydantic validation failed |
| `AUTH_REQUIRED` / `AUTH_INVALID` | 401 | Missing/invalid token |
| `REFRESH_TOKEN_REUSE` | 401 | Refresh token reuse detected |
| `FORBIDDEN` | 403 | Insufficient permissions |
| `NOT_FOUND` | 404 | Resource not found |
| `CONFLICT` | 409 | Duplicate or business rule violation |
| `RATE_LIMITED` | 429 | Too many login attempts |
| `INTERNAL_ERROR` | 500 | Unhandled exception |

---

## 6. Frontend — Detailed Functionality

### 6.1 Architecture

- **Framework:** Next.js 16 App Router with React 19 client components.
- **Styling:** Tailwind CSS 4 with CSS variables for theming (light/dark).
- **State:** React Context for auth and theme; page-level `useState`/`useEffect` for data.
- **API client:** `lib/api.js` — centralized fetch wrapper with auto token refresh.
- **Font:** DM Sans via `next/font/google`.

### 6.2 API Client (`lib/api.js`)

**Token management:**
- Stores `access_token` and `refresh_token` in `localStorage`.
- On 401, automatically calls `/auth/refresh` and retries once.
- Clears tokens on refresh failure.

**Exported methods:** 40+ wrappers covering all backend endpoints (auth, tickets, SLA, users, audit, organizations, contacts, teams, queues, notifications, reports, KB, CSAT, attachments, saved views, macros, tags).

**Error handling:** Parses backend error envelope into `ApiError` class with `code`, `message`, `status`, `details`.

### 6.3 Authentication Context (`lib/auth-context.js`)

- On mount: if access token exists, calls `/auth/me` to restore session.
- Exposes: `user`, `loading`, `login()`, `register()`, `logout()`.
- `login`/`register` store tokens then fetch user profile with permissions.

### 6.4 Permission Helpers (`lib/permissions.js`)

| Function | Purpose |
|----------|---------|
| `hasPermission(user, perm)` | Check if user has specific permission |
| `isStaff(user)` | `user_type === "staff"` or role in OWNER/ADMIN/SUPERVISOR/AGENT |
| `isCustomer(user)` | Customer roles |
| `homeForUser(user)` | Staff → `/dashboard`, customer → `/portal/tickets`, unauthenticated → `/login` |

### 6.5 Route Protection (`RequireAuth`)

- Redirects to `/login` if not authenticated.
- Optional `permissions` prop: requires at least one permission.
- Optional `roles` prop: requires matching role.
- Shows spinner while auth loading.

### 6.6 Theme (`lib/theme-context.js`)

- Light/dark mode with `localStorage` persistence.
- Respects `prefers-color-scheme` on first visit.
- Toggles `dark` class on `<html>`.

### 6.7 Pages & Features

#### `/` (Home)
- Redirects to role-appropriate home (`homeForUser`).

#### `/login`
- Email/password form.
- On success: redirect to dashboard (staff) or portal (customer).
- Link to register.

#### `/register`
- Fields: full name, email, organization name, password (min 8 chars).
- Creates new tenant; user becomes OWNER.
- Redirects to `/dashboard`.

#### `/dashboard` (Staff)
- **Permission:** authenticated (report data requires `report.view`).
- Shows 4 metric cards: open tickets, resolved, unassigned, SLA breached.
- Falls back to quick links if no report permission.

#### `/tickets` (Staff)
- Paginated ticket list (20 per page).
- Filters: status, priority.
- Shows ticket number, title, priority badge, status badge.
- Link to create new ticket.

#### `/tickets/new`
- Form: title, description, priority (P1–P4), optional category.
- Creates ticket via API, redirects to detail page.

#### `/tickets/[id]` (Staff & Customer)
- **Ticket header:** number, title, description, priority/status badges.
- **Status change:** dropdown of `allowed_transitions` from API (uses optimistic locking with version).
- **Assignment:** dropdown of agents (if `ticket.assign` permission).
- **SLA display:** status and resolution due date.
- **Comments:** threaded list with internal note highlighting (amber styling).
- **Add comment:** textarea, optional "internal note" checkbox (staff only).
- Permission-gated UI elements via `hasPermission`.

#### `/sla` (Staff)
- **Permission:** `sla.view` required to access page.
- Lists all active SLA policies with priority, response/resolution times.
- Create form (if `sla.manage`): name, priority, first response minutes, resolution hours.

#### `/customers` (Staff)
- **Permission:** `organization.manage`.
- Two-column layout: organizations list + contacts list.
- Read-only display (no create forms in UI; API supports create).

#### `/admin/users` (Admin)
- **Permission:** `user.manage`.
- Lists all users with email.
- Role dropdown: CUSTOMER, CUSTOMER ADMIN, AGENT, SUPERVISOR, ADMIN, OWNER.
- PATCH on change.

#### `/admin/audit` (Admin)
- **Permission:** `audit.view`.
- Paginated audit log with formatted action names and entity types.
- Shows actor name, entity name, timestamp.

#### `/portal/tickets` (Customer)
- Simplified ticket list (own tickets only, scoped by backend).
- Link to create ticket (note: `/portal/tickets/new` route referenced but may use `/tickets/new`).
- Links to shared ticket detail page.

#### `/portal/kb` (Customer)
- Lists knowledge base articles (public published only for customers).
- Title + body preview.

### 6.8 Navigation (`Navbar`)

- Hidden when not logged in.
- **Staff links:** Dashboard, Tickets, SLA (if permitted), Customers (if permitted), Users, Audit.
- **Customer links:** My tickets, Help (KB).
- **Settings menu:** user info, theme toggle, logout.

### 6.9 UI Component Library

Reusable components in `app/components/`:

| Component | Purpose |
|-----------|---------|
| `Button` | Primary/secondary actions |
| `Input`, `Textarea`, `Select` | Form controls with labels |
| `Card`, `ListPanel` | Content containers |
| `PageHeader`, `PageTransition` | Layout wrappers |
| `Spinner`, `EmptyState` | Loading and empty states |
| `Pagination` | Page navigation |
| `StatusBadge`, `PriorityBadge` | Ticket visual indicators |
| `AuthLayout`, `BrandMark` | Auth page branding |
| `ThemeToggle`, `SettingsMenu` | User preferences |
| `RequireAuth` | Route guard |

**Animations:** Framer Motion for page transitions, list hover effects, form field stagger.

### 6.10 Environment

```env
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
```

Baked into Docker image at build time via Jenkins `NEXT_PUBLIC_API_URL` build arg.

---

## 7. Data Model

### 7.1 Core Entities

| Table | Key Fields | Relationships |
|-------|-----------|---------------|
| `tenants` | name, slug, timezone, plan, features | Parent of all tenant data |
| `users` | email, password_hash, role, user_type, is_active | Belongs to tenant; unique email per tenant |
| `refresh_tokens` | token_hash, family_id, expires_at, revoked_at | Token rotation & reuse detection |
| `permissions` | code, description | Global permission catalog |
| `roles` | name, is_system, tenant_id | Per-tenant role definitions |
| `role_permissions` | role_id, permission_id | M:N mapping |
| `user_roles` | user_id, role_id | User role assignments |

### 7.2 Customer Management

| Table | Key Fields |
|-------|-----------|
| `organizations` | name, org_type, is_active |
| `contacts` | email, full_name, organization_id, user_id |

### 7.3 Ticket Domain

| Table | Key Fields |
|-------|-----------|
| `tickets` | ticket_number, title, description, status, priority, ticket_type, source, version, search_vector, timestamps |
| `comments` | body, is_internal, author_id |
| `categories` | name, parent_id (hierarchical) |
| `tags`, `ticket_tags` | Tagging system |
| `ticket_links` | source/target ticket, link_type |

### 7.4 SLA

| Table | Key Fields |
|-------|-----------|
| `sla_policies` | name, priority, first_response_minutes, resolution_hours |
| `sla_policy_versions` | versioned snapshots of policy timings |
| `ticket_slas` | due dates, responded/resolved/breached timestamps, status, paused_at |
| `sla_events` | event_type, details (audit trail for SLA) |

### 7.5 Operations

| Table | Key Fields |
|-------|-----------|
| `teams`, `team_members` | Team structure with leads |
| `queues` | assignment_mode (manual, etc.) |
| `audit_logs` | action, entity_type/id, old/new values, correlation_id |
| `idempotency_records` | endpoint, key, cached response |
| `jobs` | job_type, payload, status, attempts, run_at |
| `notifications` | channel, title, body, is_read, extra_data |
| `attachments` | filename, mime_type, size, checksum, storage_key |
| `automation_rules` | trigger_event, conditions, actions |
| `saved_views` | filters, is_shared |
| `macros` | reply_body, actions |
| `kb_articles` | title, body, visibility, status, version |
| `csat_ratings` | score (1–5), comment |
| `worker_heartbeats` | worker_id, last_seen_at |

---

## 8. Background Worker & Async Jobs

**Process:** `python -m app.jobs.worker`

**Loop (every `WORKER_POLL_SECONDS`, default 30s):**
1. Update worker heartbeat in `worker_heartbeats`.
2. `process_sla_breaches()` — scan active SLAs, mark breached if past due dates.
3. `process_jobs()` — dequeue pending jobs with `SELECT ... FOR UPDATE SKIP LOCKED`.

**SLA breach handling:**
- Checks `first_response_due_at` (if no response) and `resolution_due_at` (if not resolved).
- Sets `breached_at`, status `BREACHED`.
- Creates SLA events (`first_response_breached`, `resolution_breached`).
- Sends in-app notification to ticket assignee.

**Job types:** `sla_check` (runs breach processing).

**Health:** `/readyz` checks worker heartbeat within last 5 minutes.

---

## 9. DevOps & Deployment

### 9.1 Local Development

```bash
# Backend
cd backend && python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # configure DATABASE_URL, JWT_SECRET_KEY
python -m scripts.bootstrap_db
python -m uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend && npm install
cp .env.example .env.local  # NEXT_PUBLIC_API_URL
npm run dev

# Both at once
./start.sh  # or start.bat on Windows
```

### 9.2 Docker Compose

Three services on external network `naman-private-network`:

| Service | Image | Command | Port |
|---------|-------|---------|------|
| `ticket-be` | ticket-be:latest | uvicorn | 8000 |
| `ticket-worker` | ticket-be:latest | `python -m app.jobs.worker` | — |
| `ticket-fe` | ticket-fe:latest | next start | 3000 |

Environment from root `.env` file.

### 9.3 Jenkins Pipeline

**Parameters:** `BUILD_TARGET` = BOTH | BACKEND | FRONTEND

**Stages:**
1. Checkout SCM
2. Build backend Docker image (`./backend`)
3. Build frontend Docker image with `NEXT_PUBLIC_API_URL` build arg
4. Deploy via `docker compose up -d --force-recreate`
5. Verify containers running

**Production URLs:**
- Frontend: `https://ticket.namanchaturvedi.com`
- Backend: `https://ticket-be.namanchaturvedi.com`

### 9.4 Database Migrations

```bash
cd backend && alembic upgrade head
```

Initial migration: `alembic/versions/001_initial.py`

### 9.5 Testing

```bash
cd backend && pytest
```

Tests in `tests/test_unit.py` and `tests/test_api.py`.

---

## 10. API Conventions

| Convention | Details |
|------------|---------|
| **Base URL** | `/api/v1` |
| **Auth header** | `Authorization: Bearer <access_token>` |
| **Pagination** | `?page=1&size=20`, response includes `total` |
| **Idempotency** | `Idempotency-Key` header on POST tickets/comments |
| **Request tracing** | `X-Request-ID` response header |
| **CORS** | Configurable via `CORS_ORIGINS` env var |
| **File uploads** | `multipart/form-data` for attachments |

---

## 11. End-to-End Flows

### 11.1 New Organization Onboarding

```
User → /register → POST /auth/register
  → Create tenant, roles, OWNER user, org, contact
  → Seed default SLA policies (P1–P4)
  → Return JWT tokens
  → Frontend stores tokens, fetches /auth/me
  → Redirect to /dashboard
```

### 11.2 Customer Submits Ticket

```
Customer → /portal/tickets → POST /tickets
  → Ticket created (status NEW, number TCK-XXXXXX)
  → SLA attached based on priority
  → Audit logged
Customer → /tickets/{id} → views ticket, adds public comment
  → first_response_at set, SLA first_responded_at updated
```

### 11.3 Agent Resolves Ticket

```
Agent → /tickets → lists all open tickets (ticket.view)
Agent → /tickets/{id} → assigns self, changes status OPEN → IN_PROGRESS → RESOLVED
  → SLA pause/resume handled on waiting statuses
  → On RESOLVED: resolved_at set, SLA status MET/BREACHED
Agent → adds internal note (is_internal=true, visible only to staff)
Customer → sees public comments only, can transition RESOLVED → CLOSED
```

### 11.4 SLA Breach

```
Worker loop → process_sla_breaches()
  → Finds ACTIVE SLAs past due date
  → Sets breached_at, status BREACHED
  → Creates notification for assignee
Dashboard → reportSummary shows sla_breached count
```

### 11.5 Admin Role Change

```
Admin → /admin/users → PATCH /users/{id}/role
  → Validates not demoting last OWNER
  → Updates User.role and UserRole records
  → Audit: user.role_changed
  → User's permissions change on next /auth/me
```

---

## 12. Gaps & Backend-Only Features

Features implemented in the **backend API** but **not yet exposed in the frontend UI**:

| Feature | API Available | Frontend UI |
|---------|--------------|-------------|
| Ticket search (`/search/tickets`) | ✅ | ❌ (list has `q` param but UI doesn't use it) |
| Bulk ticket actions | ✅ | ❌ |
| Attachments upload/list | ✅ | ❌ |
| CSAT submission | ✅ | ❌ |
| Notifications | ✅ | ❌ |
| Automation rules | ✅ | ❌ |
| Saved views | ✅ | ❌ |
| Macros | ✅ | ❌ |
| Tags on tickets | ✅ | ❌ |
| Teams/queues management | ✅ | ❌ |
| Create organization/contact | ✅ | ❌ (customers page is read-only) |
| KB article creation | ✅ | ❌ (portal KB is read-only) |
| Ticket transitions API (version locking) | ✅ | ✅ (used when `allowed_transitions` present) |
| Customer portal new ticket route | — | `/portal/tickets/new` linked but route may not exist (uses `/tickets/new`) |

**Automation rules** are stored in DB but no execution engine fires on `ticket.created` or `ticket.status_changed` events yet.

---

## Summary

This Ticket Management System is a production-oriented **multi-tenant service desk** with:

- **Robust auth:** JWT + refresh token rotation with reuse detection
- **Fine-grained RBAC:** 30 permissions across 6 roles
- **Full ticket lifecycle:** State machine with role-based transitions, optimistic locking, SLA integration
- **Operational features:** Audit logging, idempotency, background SLA monitoring, reporting
- **Customer self-service:** Portal for tickets and knowledge base
- **Modern frontend:** Next.js with dark mode, animations, permission-aware UI
- **Deployment ready:** Docker, Jenkins CI/CD, health/readiness endpoints

The backend is feature-rich with many endpoints ready for future UI expansion; the current frontend covers the core workflows for staff (dashboard, tickets, SLA, users, audit) and customers (portal tickets, KB).
