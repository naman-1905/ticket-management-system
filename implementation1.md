# Ticket Management System — Improvement Plan

This plan builds on the current implementation and the existing improvement tracks. It keeps the original three tracks intact, adds a fourth track of new feature proposals, and re-sequences the roadmap to fit everything in.

- **Track A — Close the Gap:** wire up backend features that already exist but aren't exposed in the frontend.
- **Track B — Harden the Core:** strengthen things that exist but are incomplete or risky (security, reliability, scalability).
- **Track C — New Capabilities:** net-new features that extend the platform beyond its current scope.
- **Track D — Proposed Additions (new):** further capabilities worth adding on top of A/B/C, focused on enterprise readiness, agent productivity, and platform extensibility.

Each item includes rationale, rough effort, and dependencies so this can be sequenced into sprints.

---

## Track A — Close the Frontend/Backend Gap

These are the fastest wins: the API already supports them, only UI work is needed.

| # | Feature | What to build | Effort |
|---|---------|---------------|--------|
| A1 | **Ticket search UI** | Wire the existing `q` param into `/tickets` list page with a real search bar + debounce | S |
| A2 | **Bulk ticket actions** | Multi-select checkboxes on ticket list + bulk toolbar (assign, status, priority) using `POST /tickets/bulk` | M |
| A3 | **Attachments** | Drag-and-drop upload + file list on ticket detail page, using existing upload/list endpoints | M |
| A4 | **CSAT** | Post-resolution rating widget (emoji/star, 1–5) shown to customers on RESOLVED/CLOSED tickets | S |
| A5 | **Notifications UI** | Bell icon + dropdown panel in navbar, polling or websocket for unread count, "mark all read" | M |
| A6 | **Saved views** | "Save current filters as view" button on ticket list; sidebar of personal + shared views | M |
| A7 | **Macros** | Quick-insert macro dropdown in the comment box on ticket detail | S |
| A8 | **Tags** | Tag chips on ticket detail + tag filter on ticket list; tag management screen | M |
| A9 | **Teams & queues management** | Admin screens to create teams, assign members, create queues and set assignment mode | M |
| A10 | **Org/contact creation UI** | Add "New Organization" / "New Contact" forms to the `/customers` page (currently read-only) | S |
| A11 | **KB article authoring** | Rich-text (or markdown) editor for staff to create/edit KB articles, with visibility/status controls | M |
| A12 | **Fix `/portal/tickets/new`** | Either implement the dedicated portal route or update the link to point at `/tickets/new` consistently | S |

**Suggested order:** A1, A4, A7 (quick wins) → A3, A8, A10 → A2, A5, A6, A9, A11 → A12 cleanup.

---

## Track B — Harden the Core

Existing functionality that works but has gaps worth closing before scaling up.

| # | Area | Issue | Improvement |
|---|------|-------|-------------|
| B1 | **Automation engine** | Rules are stored but never executed | Build an execution engine that listens to `ticket.created`, `ticket.status_changed`, `comment.added` and evaluates `conditions`/`actions` (auto-assign, auto-tag, auto-reply, escalate) |
| B2 | **Rate limiting** | Login/register limiting is in-memory, won't survive multi-instance deploys | Move to Redis-backed rate limiter (also enables distributed idempotency cache) |
| B3 | **Idempotency store** | Currently DB-only, no TTL/cleanup mentioned | Add expiry + cleanup job for `idempotency_records`; consider Redis for hot path |
| B4 | **File storage** | Local filesystem only (`STORAGE_DIR`) | Add pluggable storage backend (S3/compatible object storage) for durability and multi-instance deployment |
| B5 | **Search** | `search_vector`-based search is basic | Move to Postgres full-text (`tsvector`/`tsquery` with ranking) or add proper indexing; consider pagination on search results |
| B6 | **Worker scalability** | Single polling worker, 30s loop | Add horizontal worker support with job locking (already uses `SKIP LOCKED`, extend to more job types), add retry/backoff and dead-letter handling for failed jobs |
| B7 | **Refresh token storage** | Opaque tokens work, but no admin visibility | Add "active sessions" view for users/admins to see and revoke sessions |
| B8 | **Audit log retention** | No mention of archival/retention policy | Add configurable retention + export-to-cold-storage for compliance |
| B9 | **Test coverage** | Only `test_unit.py` / `test_api.py` mentioned | Expand to cover state machine edge cases, SLA pause/resume math, permission matrix, and idempotency replay |
| B10 | **Observability** | No mention of metrics/tracing | Add structured logging correlation via `request_id`, Prometheus metrics (ticket throughput, SLA breach rate, API latency), and basic tracing |
| B11 | **CORS/secrets hygiene** | `.env`-driven, fine for now | Add secrets manager integration (e.g., Docker/K8s secrets or Vault) for `JWT_SECRET_KEY`, DB creds ahead of production hardening |

---

## Track C — New Capabilities (Add-Ons)

Net-new features that extend the platform's value proposition.

### C1. Email-to-Ticket & Email Replies
- Inbound email parsing (via IMAP poll or provider webhook, e.g., SES/SendGrid/Postmark) creates tickets or appends comments automatically.
- Outbound: replies to customers sent as email, with threading via a `Message-ID`/reply-token scheme.
- New tables: `email_channels`, `email_messages` (raw headers, thread linkage).

### C2. SLA Escalation Rules (beyond breach detection)
- Multi-step escalation chains: e.g., "if unassigned 15 min before breach, notify supervisor; if still unassigned, reassign to backup queue."
- Configurable per-priority escalation policies, reuses the automation engine (B1) as the execution mechanism.

### C3. Real-Time Updates (WebSockets / SSE)
- Live ticket updates (new comments, status changes, assignment) pushed to open ticket detail pages instead of relying on refresh.
- Live notification bell updates.
- Typing indicators for agent/customer on ticket comments (nice-to-have).

### C4. Reporting & Analytics Expansion
- Beyond the current 4-metric dashboard: agent performance (avg resolution time, tickets closed/week), SLA compliance trend over time, category/volume breakdown.
- Exportable reports (CSV/PDF) — `report.export` permission already exists but has no UI/backing.
- Time-series charts (ticket volume, breach rate) with date-range filters.

### C5. Customer Satisfaction Analytics
- Aggregate CSAT dashboard (average score, trend, breakdown by agent/team) — data (`csat_ratings`) already exists, just needs a reporting layer.

### C6. Multi-Channel Ticket Sources
- Extend `source` field usage: web widget (embeddable chat/ticket form for customer websites), Slack/Teams integration for internal ticket creation, API-key based programmatic ticket creation for integrations.

### C7. Round-Robin / Load-Based Auto-Assignment
- Extend `queues.assignment_mode` beyond "manual" to support round-robin and load-balanced (fewest open tickets) assignment, executed on ticket creation or via automation rules.

### C8. Ticket Merging & Linking (UI)
- `ticket_links` table exists in the data model but isn't described in the API/UI — add "merge duplicate," "link related," and "block/blocked-by" relationships with UI on the ticket detail page.

### C9. Custom Fields
- Allow tenants to define custom fields per ticket type/category (text, number, dropdown) for industry-specific data capture, stored as JSONB on `tickets` with a schema table (`custom_field_definitions`).

### C10. Approval Workflows
- Optional "requires approval" step before certain transitions (e.g., RESOLVED → CLOSED for high-priority tickets, or CANCELLED), with an approver role and audit trail.

### C11. Customer Self-Service Enhancements
- KB search with suggested articles while a customer types a new ticket ("deflection" flow).
- Ticket status tracking via a public link (no login) for guest/anonymous submissions, if desired.

### C12. AI-Assisted Features (optional, phased)
- Suggested replies / macro suggestions based on ticket content.
- Auto-categorization and auto-priority suggestion on ticket creation.
- Summarization of long comment threads for agents picking up a ticket.
- These should be additive and reviewable — agent confirms before anything is sent to a customer.

### C13. Public API & Webhooks for Integrations
- Outbound webhooks on key events (`ticket.created`, `ticket.status_changed`, `sla.breached`) so external systems (CRM, billing) can subscribe.
- API key management UI for tenants to generate scoped keys for programmatic access (distinct from user JWTs).

### C14. Mobile-Friendly / PWA
- Responsive pass on staff and customer views for tablet/mobile use (agents on the go, customers checking ticket status).
- Optional installable PWA with push notifications for ticket updates.

---

## Track D — Proposed Additions (New)

New feature ideas layered on top of Tracks A–C, aimed at closing gaps those tracks don't cover: agent-facing productivity, multi-tenant/enterprise needs, data lifecycle, and platform extensibility.

### D1. Unified Agent Inbox / Omnichannel View
- A single "my work" queue that blends assigned tickets, @mentions, SLA-at-risk items, and (once C1/C6 land) email/chat/Slack-sourced tickets into one prioritized list, instead of agents checking multiple filtered views.
- Keyboard-shortcut driven triage (next/prev, quick-assign, quick-close) for high-volume teams.
- Depends on: A5 (notifications), C1/C6 (multi-channel), B1 (automation) for smart prioritization.

### D2. SLA & Business Hours Calendar
- Configurable business calendars (per team/queue) with holidays and working hours, so SLA timers pause/resume correctly instead of assuming 24/7 coverage.
- Per-customer or per-contract SLA overrides (e.g., premium support tier gets tighter targets).
- Depends on: existing SLA breach detection logic; feeds into C2 (escalation rules) and B1.

### D3. Role-Based Dashboards & Permission Refinement
- Distinct home views for agent / team lead / admin, each surfacing the metrics and queues relevant to that role.
- Finer-grained permissions (e.g., "can view reports" vs. "can export reports," "can reassign others' tickets") beyond the current permission set, with an admin-facing permission matrix editor.
- Depends on: C4 (analytics expansion), existing permission system.

### D4. Multi-Tenancy & White-Labeling
- If the system will serve multiple customer organizations independently: tenant isolation at the data layer, per-tenant branding (logo, colors, custom domain for the customer portal), and tenant-level plan/quota limits.
- This is a foundational decision best made explicit even if deferred — retrofitting tenancy later is expensive.
- Depends on: B4 (object storage), B11 (secrets hygiene), touches most other tracks.

### D5. Data Import/Export & Migration Tooling
- Bulk CSV import for tickets/contacts/organizations (for teams migrating from another helpdesk).
- Scheduled or on-demand full data export (GDPR/portability, backups, BI pipelines).
- Depends on: B5 (search indexing should be rebuildable), C13 (can reuse API auth for export jobs).

### D6. GDPR / Data Privacy Tooling
- "Right to be forgotten" workflow — redact or anonymize a contact's PII across tickets, comments, and attachments while preserving ticket history structure.
- Data retention policies per data type (tickets, attachments, audit logs), with configurable auto-purge.
- Depends on: B8 (audit log retention), B4 (storage), D5 (export before purge).

### D7. In-App Agent Collaboration
- Internal (non-customer-visible) notes and @mentions on tickets, separate from public comments.
- "Watchers" — let agents follow a ticket without being assigned, get notified on updates.
- Depends on: A5 (notifications), C3 (real-time) for a good experience.

### D8. Knowledge Base Versioning & Feedback Loop
- Version history and rollback for KB articles (builds on A11's editor).
- "Was this helpful?" widget on customer-facing articles feeding a simple helpfulness score, surfaced to KB authors to find stale/unclear content.
- Depends on: A11 (KB authoring).

### D9. Advanced Search & Filtering
- Saved/complex filter builder (AND/OR groups, date ranges, custom field filters once D-level or C9 custom fields exist) beyond the current basic query param search.
- Global search across tickets, KB articles, and customers from one search bar.
- Depends on: B5 (full-text search), C9 (custom fields) for filtering on them.

### D10. Billing / Usage Metering (if commercial SaaS)
- If this becomes a paid product: usage metering (tickets/agents/storage per tenant), plan tiers, and integration with a billing provider (e.g., Stripe) for subscription management.
- Only relevant under the D4 multi-tenant model; skip if this is a single-org internal tool.

### D11. Chaos/Load Testing & Capacity Planning
- Load testing harness simulating concurrent ticket creation/updates to validate B6 (worker scaling) and B2/B3 (Redis) changes before they're relied on in production.
- Basic capacity planning doc (expected tickets/day, storage growth, DB sizing) to catch scaling issues before B4/B6 work is scoped.

### D12. Accessibility (a11y) Pass
- Keyboard navigation, screen-reader labeling, and color-contrast audit across the staff and customer portal UIs — easy to defer, expensive to retrofit if delayed too long, and often a compliance requirement for enterprise customers.
- Pairs naturally with C14 (mobile/PWA responsive work).

---

## Suggested Roadmap (Phased)

**Phase 1 (Quick wins, 2–3 sprints)**
A1, A4, A7, A10, A12, B9 (start expanding tests alongside each feature)

**Phase 2 (Core gap closure, 3–4 sprints)**
A2, A3, A5, A6, A8, A9, A11, B2, B3

**Phase 3 (Engine & reliability, 3–4 sprints)**
B1 (automation engine) → unlocks C2 (SLA escalation), B4 (object storage), B6 (worker scaling), B10 (observability), D2 (SLA calendars, pairs naturally with B1/C2)

**Phase 4 (Growth features, ongoing)**
C1 (email-to-ticket), C3 (real-time), C4/C5 (analytics), C7 (auto-assignment), C8 (merge/link UI), D1 (unified agent inbox), D7 (internal collaboration)

**Phase 5 (Platform maturity)**
C9 (custom fields), C10 (approvals), C13 (webhooks/API keys), C6 (multi-channel), C11 (deflection), D3 (role dashboards/permissions), D9 (advanced search), D8 (KB versioning)

**Phase 6 (Differentiators & enterprise readiness)**
C12 (AI assistance), C14 (mobile/PWA), D4 (multi-tenancy — decide early even if built late), D5 (import/export), D6 (GDPR tooling), D10 (billing, if applicable), D11 (load testing), D12 (accessibility)

---

## Notes on Sequencing Logic

- **B1 (automation engine)** is a force-multiplier — build it before C2 and before investing further in "automation.manage" UI, since escalation and auto-assignment both want to reuse it rather than duplicating rule logic.
- **B2/B3 (Redis)** should land before any horizontal scaling of backend/worker instances, since in-memory rate limiting and DB-polled idempotency won't behave correctly across multiple processes.
- **B4 (object storage)** is a prerequisite for any multi-instance or container-orchestrated (e.g., Kubernetes) deployment, since local filesystem storage won't survive pod rescheduling.
- **D4 (multi-tenancy)** is a structural decision, not just a feature — if there's any chance this becomes a multi-org product, decide the tenancy model early (even if implementation is deferred to Phase 6), since retrofitting it after data model and auth are built around single-tenant assumptions is far more expensive than building it in from the start.
- **D2 (business hours/SLA calendars)** should land alongside or just after B1, since C2's escalation chains are only as accurate as the underlying SLA clock.
- **D6 (GDPR tooling)** depends on D5 (export) existing first, since a defensible "right to be forgotten" flow should be able to export a copy before redacting.
- Track A items are largely independent of each other and can be parallelized across contributors; most Track D items are similarly independent except where noted above.