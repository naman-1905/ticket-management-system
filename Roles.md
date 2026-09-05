# Roles & Permissions

This document describes every role in the Ticket Management System, the permissions each role receives, and how those permissions map to application sections (UI pages and API endpoints).

Permissions are enforced in two places:

1. **Backend (authoritative)** — FastAPI route dependencies and service-layer checks via `user_has_permission()`.
2. **Frontend (UX)** — Navigation links, page guards (`RequireAuth`), and conditional UI elements via `hasPermission()`.

A user’s effective permissions are resolved from `user_roles` → `role_permissions` → `permissions`. If no role rows exist, the system falls back to the default mapping in `backend/app/core/permissions.py`.

---

## User types

Every account belongs to a **tenant** (organization) and has a `user_type`:

| User type | Roles | Default landing page |
| --------- | ----- | -------------------- |
| `staff` | OWNER, ADMIN, SUPERVISOR, AGENT | `/dashboard` |
| `customer` | CUSTOMER, CUSTOMER_ADMIN | `/portal/tickets` |

Staff users see the agent workspace (dashboard, ticket queue, admin tools). Customer users see the self-service portal.

---

## Roles overview

| Role | Type | Summary |
| ---- | ---- | ------- |
| **OWNER** | Staff | Full tenant access. All 33 permissions. Assigned to the first user who registers a tenant. |
| **ADMIN** | Staff | Nearly full access. Same as OWNER except **no** `sla.override`. |
| **SUPERVISOR** | Staff | Team lead / queue manager. Ticket operations, SLA override, reporting, audit, org/contact management, automations. |
| **AGENT** | Staff | Front-line support. Ticket handling, comments, SLA viewing, basic reports, knowledge base. |
| **CUSTOMER** | Customer | Self-service portal. Own tickets, create tickets, public comments, published KB articles. |
| **CUSTOMER_ADMIN** | Customer | Same as CUSTOMER plus contact management within their organization. |

### Platform admin (special flag)

Users with `is_platform_admin = true` bypass **all** permission checks across every tenant. This flag is stored in the database only and is not exposed through the API or UI. It is intended for platform operators, not tenant administrators.

---

## Permission catalog

There are **33 permissions** in the system. Each permission controls access to one or more API operations and UI features.

### Tickets

| Permission | Description |
| ---------- | ----------- |
| `ticket.view` | View all tickets in the tenant (staff queue). |
| `ticket.view_own` | View only tickets the user created, owns as customer, or submitted via their contact record. |
| `ticket.create` | Create new tickets. |
| `ticket.update` | Update ticket fields; required for bulk ticket actions. |
| `ticket.assign` | Assign tickets to agents, teams, or queues. |
| `ticket.delete` | Delete tickets. *(Defined in catalog; not yet wired to an API endpoint.)* |
| `ticket.merge` | Merge duplicate tickets. *(Defined in catalog; not yet wired to an API endpoint.)* |
| `ticket.escalate` | Escalate tickets. *(Defined in catalog; not yet wired to an API endpoint.)* |
| `ticket.transition` | Change ticket status (staff workflow transitions). |

### Comments

| Permission | Description |
| ---------- | ----------- |
| `comment.public.write` | Add public comments visible to customers. |
| `comment.internal.read` | Read internal (staff-only) notes on a ticket. |
| `comment.internal.write` | Add internal notes not visible to customers. |

### SLA

| Permission | Description |
| ---------- | ----------- |
| `sla.view` | View SLA policies and per-ticket SLA status. |
| `sla.manage` | Create, update, and deactivate SLA policies. |
| `sla.override` | Override SLA deadlines. *(Defined in catalog; not yet wired to a dedicated API endpoint.)* |

### Users & teams

| Permission | Description |
| ---------- | ----------- |
| `user.manage` | List users and change roles. |
| `team.manage` | List and create teams; add/remove team members. |
| `queue.manage` | List and create ticket queues. |

### Reporting & audit

| Permission | Description |
| ---------- | ----------- |
| `report.view` | View dashboard summary metrics. |
| `report.export` | Export reports. *(Defined in catalog; not yet wired to an API endpoint.)* |
| `audit.view` | View the audit log. |

### Organizations & contacts

| Permission | Description |
| ---------- | ----------- |
| `organization.manage` | List and create customer organizations. |
| `contact.manage` | List and create contacts. |

### Knowledge base

| Permission | Description |
| ---------- | ----------- |
| `kb.view` | View published public knowledge base articles. |
| `kb.manage` | Create articles; view draft and internal articles. |

### Automations & events

| Permission | Description |
| ---------- | ----------- |
| `automation.manage` | List and create automation rules. |
| `event.view` | List domain events. |
| `event.admin` | View dead-letter queue and retry failed event deliveries. |

### Settings & notifications

| Permission | Description |
| ---------- | ----------- |
| `settings.manage` | Manage tenant settings. *(Defined in catalog; not yet wired to an API endpoint.)* |
| `notification.manage` | Manage notification preferences/templates. *(Defined in catalog; not yet wired to an API endpoint.)* |

---

## Role → permission matrix

✓ = permission granted · — = not granted

| Permission | OWNER | ADMIN | SUPERVISOR | AGENT | CUSTOMER | CUSTOMER_ADMIN |
| ---------- | :---: | :---: | :--------: | :---: | :------: | :------------: |
| `ticket.view` | ✓ | ✓ | ✓ | ✓ | — | — |
| `ticket.view_own` | ✓ | ✓ | — | — | ✓ | ✓ |
| `ticket.create` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| `ticket.update` | ✓ | ✓ | — | ✓ | — | — |
| `ticket.assign` | ✓ | ✓ | ✓ | ✓ | — | — |
| `ticket.delete` | ✓ | ✓ | — | — | — | — |
| `ticket.merge` | ✓ | ✓ | — | — | — | — |
| `ticket.escalate` | ✓ | ✓ | — | — | — | — |
| `ticket.transition` | ✓ | ✓ | ✓ | ✓ | — | — |
| `comment.public.write` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| `comment.internal.read` | ✓ | ✓ | ✓ | ✓ | — | — |
| `comment.internal.write` | ✓ | ✓ | ✓ | ✓ | — | — |
| `sla.view` | ✓ | ✓ | ✓ | ✓ | — | — |
| `sla.manage` | ✓ | ✓ | — | — | — | — |
| `sla.override` | ✓ | — | ✓ | — | — | — |
| `user.manage` | ✓ | ✓ | — | — | — | — |
| `team.manage` | ✓ | ✓ | ✓ | — | — | — |
| `queue.manage` | ✓ | ✓ | ✓ | — | — | — |
| `report.view` | ✓ | ✓ | ✓ | ✓ | — | — |
| `report.export` | ✓ | ✓ | ✓ | — | — | — |
| `audit.view` | ✓ | ✓ | ✓ | — | — | — |
| `settings.manage` | ✓ | ✓ | — | — | — | — |
| `organization.manage` | ✓ | ✓ | ✓ | — | — | — |
| `contact.manage` | ✓ | ✓ | ✓ | — | — | ✓ |
| `automation.manage` | ✓ | ✓ | ✓ | — | — | — |
| `kb.manage` | ✓ | ✓ | ✓ | ✓ | — | — |
| `kb.view` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| `notification.manage` | ✓ | ✓ | ✓ | — | — | — |
| `event.view` | ✓ | ✓ | — | — | — | — |
| `event.admin` | ✓ | ✓ | — | — | — | — |

---

## Application sections

This section maps each area of the application to the permissions required to use it.

### Authentication (`/login`, `/register`)

| Action | Required permission / rule | Who has access |
| ------ | ------------------------ | -------------- |
| Register a new tenant | None (public) | Anyone. First user becomes **OWNER**. |
| Log in | Valid credentials | All roles. |
| View own profile (`GET /auth/me`) | Authenticated | All roles. |
| Log out | Authenticated | All roles. |

After login, staff are redirected to `/dashboard`; customers to `/portal/tickets`.

---

### Navigation bar

The navbar shows links based on role type and permissions:

| Nav link | Route | Visible when |
| -------- | ----- | ------------ |
| Dashboard | `/dashboard` | Staff (`user_type = staff`) |
| Tickets | `/tickets` | Staff |
| SLA | `/sla` | Staff + `sla.view` |
| Customers | `/customers` | Staff + `organization.manage` |
| Users | `/admin/users` | `user.manage` |
| Audit | `/admin/audit` | `audit.view` |
| My tickets | `/portal/tickets` | Customer |
| Help | `/portal/kb` | Customer |

**By role:**

| Role | Nav links shown |
| ---- | --------------- |
| OWNER | Dashboard, Tickets, SLA, Customers, Users, Audit |
| ADMIN | Dashboard, Tickets, SLA, Customers, Users, Audit |
| SUPERVISOR | Dashboard, Tickets, SLA, Customers |
| AGENT | Dashboard, Tickets, SLA |
| CUSTOMER | My tickets, Help |
| CUSTOMER_ADMIN | My tickets, Help |

---

### Dashboard (`/dashboard`)

| Feature | Permission | OWNER | ADMIN | SUPERVISOR | AGENT | CUSTOMER | CUSTOMER_ADMIN |
| ------- | ---------- | :---: | :---: | :--------: | :---: | :------: | :------------: |
| Access page | Authenticated (staff) | ✓ | ✓ | ✓ | ✓ | — | — |
| View summary cards (open, resolved, unassigned, SLA breached) | `report.view` | ✓ | ✓ | ✓ | ✓ | — | — |
| Quick links (view tickets, new ticket) | Fallback when no `report.view` | — | — | — | — | — | — |

**API:** `GET /api/v1/reports/tickets/summary` requires `report.view`.

Agents without `report.view` would see quick links only, but all staff roles that can reach the dashboard currently have `report.view`.

---

### Tickets — list (`/tickets`)

| Feature | Permission | OWNER | ADMIN | SUPERVISOR | AGENT | CUSTOMER | CUSTOMER_ADMIN |
| ------- | ---------- | :---: | :---: | :--------: | :---: | :------: | :------------: |
| Access page | Staff (implicit via nav) | ✓ | ✓ | ✓ | ✓ | — | — |
| List all tenant tickets | `ticket.view` | ✓ | ✓ | ✓ | ✓ | — | — |
| Filter by status, priority, search | `ticket.view` | ✓ | ✓ | ✓ | ✓ | — | — |
| See assignee name in list | `ticket.view` | ✓ | ✓ | ✓ | ✓ | — | — |
| Link to create ticket | `ticket.create` | ✓ | ✓ | ✓ | ✓ | — | — |

**API:** `GET /api/v1/tickets` — requires `ticket.view` (all tickets) or `ticket.view_own` (scoped to own tickets).

---

### Tickets — create (`/tickets/new`)

| Feature | Permission | OWNER | ADMIN | SUPERVISOR | AGENT | CUSTOMER | CUSTOMER_ADMIN |
| ------- | ---------- | :---: | :---: | :--------: | :---: | :------: | :------------: |
| Access page | Authenticated | ✓ | ✓ | ✓ | ✓ | — | — |
| Submit new ticket | `ticket.create` | ✓ | ✓ | ✓ | ✓ | — | — |

Staff-created tickets are associated with the requester contact linked to the creating user.

**API:** `POST /api/v1/tickets` requires `ticket.create`.

---

### Tickets — detail (`/tickets/[id]`)

Shared by staff and customers (customers reach it from the portal ticket list).

| Feature | Permission | OWNER | ADMIN | SUPERVISOR | AGENT | CUSTOMER | CUSTOMER_ADMIN |
| ------- | ---------- | :---: | :---: | :--------: | :---: | :------: | :------------: |
| View ticket | `ticket.view` or `ticket.view_own` | ✓ | ✓ | ✓ | ✓ | ✓ (own) | ✓ (own) |
| View SLA status on ticket | Ticket access | ✓ | ✓ | ✓ | ✓ | ✓ (own) | ✓ (own) |
| Change status | `ticket.transition` | ✓ | ✓ | ✓ | ✓ | —* | —* |
| Assign to agent | `ticket.assign` | ✓ | ✓ | ✓ | ✓ | — | — |
| View internal comments | `comment.internal.read` | ✓ | ✓ | ✓ | ✓ | — | — |
| Add public comment | `comment.public.write` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Add internal note | `comment.internal.write` | ✓ | ✓ | ✓ | ✓ | — | — |
| Use macros (canned replies) | Authenticated + ticket access | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Submit CSAT rating | Ticket access (resolved/closed) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Upload / download attachments | Ticket access | ✓ | ✓ | ✓ | ✓ | ✓ (own) | ✓ (own) |

\* Customers can change status only through **limited lifecycle transitions** allowed for the CUSTOMER role (e.g. close a resolved ticket, cancel an open ticket). This uses `ticket.view_own` plus role-based transition rules, not `ticket.transition`.

**API endpoints:**

| Endpoint | Permission |
| -------- | ---------- |
| `GET /api/v1/tickets/{id}` | `ticket.view` or `ticket.view_own` |
| `POST /api/v1/tickets/{id}/transitions` | `ticket.transition` or `ticket.view_own` + allowed customer transition |
| `POST /api/v1/tickets/{id}/assign` | `ticket.assign` |
| `GET /api/v1/tickets/{id}/comments` | Ticket access; internal comments filtered without `comment.internal.read` |
| `POST /api/v1/tickets/{id}/comments` | `comment.public.write` or `comment.internal.write` |
| `GET /api/v1/tickets/{id}/sla` | Ticket access |
| `POST /api/v1/attachments/tickets/{id}` | Ticket access |
| `GET /api/v1/attachments/tickets/{id}` | Ticket access |
| `POST /api/v1/csat/tickets/{id}` | Ticket access |
| `POST /api/v1/tickets/bulk` | `ticket.update` |

---

### Ticket status transitions by role

Allowed transitions depend on the user’s **role**, independent of most permissions. Staff with `ticket.transition` must still follow these rules; customers use a smaller subset.

| Role | Example allowed transitions |
| ---- | --------------------------- |
| **CUSTOMER** | NEW → OPEN, CANCELLED; OPEN → CANCELLED; RESOLVED → CLOSED |
| **AGENT** | Full agent workflow: OPEN ↔ IN_PROGRESS, waiting states, RESOLVED, CLOSED, etc. |
| **SUPERVISOR** | Same as AGENT |
| **ADMIN / OWNER** | Broadest set, including CANCELLED from most states and reopening closed tickets |

Full transition maps are defined in `backend/app/domain/ticket_lifecycle.py`.

---

### SLA management (`/sla`)

| Feature | Permission | OWNER | ADMIN | SUPERVISOR | AGENT | CUSTOMER | CUSTOMER_ADMIN |
| ------- | ---------- | :---: | :---: | :--------: | :---: | :------: | :------------: |
| Access page | `sla.view` | ✓ | ✓ | ✓ | ✓ | — | — |
| View SLA policies | `sla.view` | ✓ | ✓ | ✓ | ✓ | — | — |
| Create policy | `sla.manage` | ✓ | ✓ | — | — | — | — |
| Edit policy | `sla.manage` | ✓ | ✓ | — | — | — | — |
| Deactivate policy | `sla.manage` | ✓ | ✓ | — | — | — | — |

**API:**

| Endpoint | Permission |
| -------- | ---------- |
| `GET /api/v1/sla/policies` | `sla.view` |
| `POST /api/v1/sla/policies` | `sla.manage` |
| `PATCH /api/v1/sla/policies/{id}` | `sla.manage` |
| `DELETE /api/v1/sla/policies/{id}` | `sla.manage` |

---

### Customers (`/customers`)

Organizations and contacts management. The page is accessible to staff; individual features depend on permissions.

| Feature | Permission | OWNER | ADMIN | SUPERVISOR | AGENT | CUSTOMER | CUSTOMER_ADMIN |
| ------- | ---------- | :---: | :---: | :--------: | :---: | :------: | :------------: |
| Access page | `organization.manage` **or** `contact.manage` | ✓ | ✓ | ✓ | — | — | — |
| List organizations | `organization.manage` | ✓ | ✓ | ✓ | — | — | — |
| Create organization | `organization.manage` | ✓ | ✓ | ✓ | — | — | — |
| List contacts | `contact.manage` | ✓ | ✓ | ✓ | — | — | — |
| Create contact | `contact.manage` | ✓ | ✓ | ✓ | — | — | ✓* |

\* CUSTOMER_ADMIN has `contact.manage` but is a customer user type and does not see the staff Customers page in the navbar. They would need API access or a future portal UI to use this permission.

**API:**

| Endpoint | Permission |
| -------- | ---------- |
| `GET /api/v1/organizations` | `organization.manage` |
| `POST /api/v1/organizations` | `organization.manage` |
| `GET /api/v1/contacts` | `contact.manage` |
| `POST /api/v1/contacts` | `contact.manage` |

---

### User management (`/admin/users`)

| Feature | Permission | OWNER | ADMIN | SUPERVISOR | AGENT | CUSTOMER | CUSTOMER_ADMIN |
| ------- | ---------- | :---: | :---: | :--------: | :---: | :------: | :------------: |
| Access page | `user.manage` | ✓ | ✓ | — | — | — | — |
| List all tenant users | `user.manage` | ✓ | ✓ | — | — | — | — |
| Change user role | `user.manage` | ✓ | ✓ | — | — | — | — |

**Rules:**

- Requires `user.manage`.
- Cannot demote the **last active OWNER** in a tenant (API returns 409 Conflict).
- All six roles (OWNER, ADMIN, SUPERVISOR, AGENT, CUSTOMER, CUSTOMER_ADMIN) can be assigned.

**API:**

| Endpoint | Permission |
| -------- | ---------- |
| `GET /api/v1/users` | `user.manage` |
| `PATCH /api/v1/users/{id}/role` | `user.manage` |
| `GET /api/v1/users/agents` | `ticket.assign` (used for assignment dropdown) |

---

### Audit log (`/admin/audit`)

| Feature | Permission | OWNER | ADMIN | SUPERVISOR | AGENT | CUSTOMER | CUSTOMER_ADMIN |
| ------- | ---------- | :---: | :---: | :--------: | :---: | :------: | :------------: |
| Access page | `audit.view` | ✓ | ✓ | ✓ | — | — | — |
| View paginated audit entries | `audit.view` | ✓ | ✓ | ✓ | — | — | — |

Logs include actions such as ticket creation, status changes, role changes, SLA policy changes, and contact creation.

**API:** `GET /api/v1/audit/logs` requires `audit.view`.

---

### Customer portal — my tickets (`/portal/tickets`)

| Feature | Permission | OWNER | ADMIN | SUPERVISOR | AGENT | CUSTOMER | CUSTOMER_ADMIN |
| ------- | ---------- | :---: | :---: | :--------: | :---: | :------: | :------------: |
| Access page | Customer user type | — | — | — | — | ✓ | ✓ |
| List own tickets | `ticket.view_own` | — | — | — | — | ✓ | ✓ |
| Open ticket detail | `ticket.view_own` | — | — | — | — | ✓ | ✓ |

---

### Customer portal — new ticket (`/portal/tickets/new`)

| Feature | Permission | OWNER | ADMIN | SUPERVISOR | AGENT | CUSTOMER | CUSTOMER_ADMIN |
| ------- | ---------- | :---: | :---: | :--------: | :---: | :------: | :------------: |
| Access page | Customer user type | — | — | — | — | ✓ | ✓ |
| Submit ticket | `ticket.create` | — | — | — | — | ✓ | ✓ |

---

### Customer portal — knowledge base (`/portal/kb`)

| Feature | Permission | OWNER | ADMIN | SUPERVISOR | AGENT | CUSTOMER | CUSTOMER_ADMIN |
| ------- | ---------- | :---: | :---: | :--------: | :---: | :------: | :------------: |
| Access page | Customer user type | — | — | — | — | ✓ | ✓ |
| View published public articles | `kb.view` | — | — | — | — | ✓ | ✓ |

**API:** `GET /api/v1/kb/articles` — without `kb.manage`, only `visibility = public` and `status = published` articles are returned.

---

## API-only features (no dedicated UI page)

These capabilities are available through the REST API but do not yet have a dedicated frontend section.

### Teams (`/api/v1/teams`)

| Action | Permission | OWNER | ADMIN | SUPERVISOR | AGENT |
| ------ | ---------- | :---: | :---: | :--------: | :---: |
| List teams | `team.manage` | ✓ | ✓ | ✓ | — |
| Create team | `team.manage` | ✓ | ✓ | ✓ | — |
| Add/remove member | `team.manage` | ✓ | ✓ | ✓ | — |

### Queues (`/api/v1/queues`)

| Action | Permission | OWNER | ADMIN | SUPERVISOR | AGENT |
| ------ | ---------- | :---: | :---: | :--------: | :---: |
| List queues | `queue.manage` | ✓ | ✓ | ✓ | — |
| Create queue | `queue.manage` | ✓ | ✓ | ✓ | — |

### Automations (`/api/v1/automations`)

| Action | Permission | OWNER | ADMIN | SUPERVISOR | AGENT |
| ------ | ---------- | :---: | :---: | :--------: | :---: |
| List/create rules | `automation.manage` | ✓ | ✓ | ✓ | — |

### Knowledge base — staff management (`/api/v1/kb`)

| Action | Permission | OWNER | ADMIN | SUPERVISOR | AGENT |
| ------ | ---------- | :---: | :---: | :--------: | :---: |
| List all articles (incl. drafts) | `kb.manage` | ✓ | ✓ | ✓ | ✓ |
| Create article | `kb.manage` | ✓ | ✓ | ✓ | ✓ |
| View non-public article | `kb.manage` | ✓ | ✓ | ✓ | ✓ |

### Events (`/api/v1/events`)

| Action | Permission | OWNER | ADMIN | SUPERVISOR | AGENT |
| ------ | ---------- | :---: | :---: | :--------: | :---: |
| List events | `event.view` | ✓ | ✓ | — | — |
| List dead letters | `event.admin` | ✓ | ✓ | — | — |
| Retry dead letter | `event.admin` | ✓ | ✓ | — | — |

### Search (`/api/v1/search`)

| Action | Permission | Notes |
| ------ | ---------- | ----- |
| Search tickets | `ticket.view` | Staff only. Customers use the ticket list with `ticket.view_own`. |

### Notifications (`/api/v1/notifications`)

| Action | Permission | Notes |
| ------ | ---------- | ----- |
| List own notifications | Authenticated | All roles. |
| Mark all read | Authenticated | All roles. |
| Manage notification settings | `notification.manage` | OWNER, ADMIN, SUPERVISOR. No UI yet. |

### Macros, tags, and saved views (`/api/v1/automations`)

| Action | Permission | Notes |
| ------ | ---------- | ----- |
| List/create macros | Authenticated | Used in ticket detail UI by any user with ticket access. |
| List/create tags | Authenticated | API available; no dedicated UI. |
| Add tag to ticket | Authenticated + ticket access | API available. |
| List/create saved views | Authenticated | Per-user or shared views. No dedicated UI. |

---

## Permissions reserved for future use

The following permissions exist in the catalog and are assigned to roles, but are **not yet enforced** by any API endpoint or UI control:

| Permission | Intended use |
| ---------- | ------------ |
| `ticket.delete` | Hard-delete tickets |
| `ticket.merge` | Merge duplicate tickets |
| `ticket.escalate` | Escalate to another team or priority |
| `sla.override` | Manually extend or waive SLA deadlines |
| `report.export` | Export report data (CSV, PDF) |
| `settings.manage` | Tenant-wide configuration (branding, features, etc.) |
| `notification.manage` | Notification templates and delivery settings |

OWNER and ADMIN receive these permissions so they are ready when the features are implemented. SUPERVISOR receives `sla.override` and `report.export` but not the others.

---

## Managing roles

### Create the first administrator

Register at `/register` or call `POST /api/v1/auth/register`. The registering user becomes **OWNER** of a new tenant with all permissions.

### Change an existing user’s role

1. Log in as a user with `user.manage` (OWNER or ADMIN).
2. Go to **Users** (`/admin/users`) or call `PATCH /api/v1/users/{id}/role` with `{ "role": "AGENT" }`.

### Promote to platform admin

Direct database update only:

```sql
UPDATE users SET is_platform_admin = true WHERE email = 'user@example.com';
```

---

## Source of truth

| Artifact | Location |
| -------- | -------- |
| Permission catalog & default role mappings | `backend/app/core/permissions.py` |
| Permission enforcement (API) | `backend/app/deps.py`, `backend/app/services/tenancy.py` |
| Ticket access & comment rules | `backend/app/services/tickets.py` |
| Status transition rules | `backend/app/domain/ticket_lifecycle.py` |
| Frontend permission helpers | `frontend/lib/permissions.js` |
| Role enum (UI) | `frontend/lib/constants.js` |

When adding a new feature, define the permission in `permissions.py`, assign it to roles in `DEFAULT_ROLES`, enforce it on the API route, and gate the UI with `hasPermission()` or `RequireAuth permissions={[...]}`.
