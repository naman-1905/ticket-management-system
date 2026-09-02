# Ticket Management System — Next-Generation Expansion Plan

> **Audit note on sourcing:** No source repository was available in this session — only two documents were provided: the current `implementation1.md` (Tracks A–D) and a comprehensive project summary describing the live architecture (FastAPI/Postgres backend, Next.js frontend, worker process, permission catalog, ticket state machine, SLA engine). This plan treats those two documents as the verified baseline. Any assumption not directly traceable to them is explicitly marked **[Assumed]**. A coding agent implementing this plan should re-verify schema/route names against the actual codebase before writing migrations.

---

## 1. Purpose

`implementation1.md` turns the existing codebase into a solid, single-service **help desk**: it closes frontend/backend gaps, hardens reliability (Redis, object storage, worker scaling), and adds adjacent features that any mature help desk needs (email-to-ticket, real-time updates, custom fields, approvals, webhooks, multi-tenancy, GDPR tooling).

None of that makes the product an **ITSM / Service Desk platform** in the sense that IT operations, MSPs, or enterprise support organizations mean the term. A help desk resolves tickets. A service desk platform manages the lifecycle of **incidents, problems, changes, assets, services, and requests as distinct, interrelated domain objects**, with governance, workforce, and quality layers on top. Those domains are structurally absent from the current data model — they cannot be reached by exposing more UI on existing tables (Track A) or hardening existing subsystems (Track B), and they are materially different from the generic productivity/extensibility features in Tracks C/D.

This document exists to specify that missing layer: new bounded domains (Incident, Problem, Change, Asset/CMDB, Service Catalog, Request Fulfillment, Work/Task, Contract/Entitlement, Workforce, Quality Assurance), the two cross-cutting engines that make them tractable to build without duplicating logic five times (a generic Workflow Orchestration engine and an Event-Driven/outbox architecture), and the operational layers (Security Operations, DevOps-triggered incidents, AI ops classified by autonomy level) that turn the platform into something an enterprise buyer would recognize as ITSM.

Everything here is additive to, and depends on, the platform `implementation1.md` produces (automation engine, SLA engine, notifications, RBAC, multi-tenancy, audit log, object storage, event/webhook plumbing where noted). Nothing here modifies `implementation1.md` or re-specifies work it already owns.

---

## 2. Current Platform Boundary

The following is explicitly **in scope for `implementation1.md`** and is **out of scope here** — it is not re-specified, renamed, or extended in this document except where a new domain must *reference* it (e.g., "an Incident links to Tickets" assumes tickets already exist):

- Ticket CRUD, the existing 9-state ticket lifecycle/state machine, optimistic locking via `version`
- RBAC: 30-permission catalog, 6 system roles, `role_permissions`/`user_roles`
- SLA policies, breach detection, pause/resume, escalation chains (Track C2), business-hours/SLA calendars (Track D2)
- Automation rule engine execution (Track B1) — trigger/condition/action model on ticket events
- Notifications (in-app), real-time updates via WebSocket/SSE (Track C3)
- Reporting/analytics dashboard, CSAT (Tracks C4/C5)
- Email-to-ticket, multi-channel sources, API-key ticket creation (Tracks C1/C6)
- Round-robin/load-based auto-assignment on **tickets** (Track C7)
- Ticket merging/linking UI, custom fields on tickets, approval workflows as a generic gate (Tracks C8/C9/C10)
- Customer self-service portal, KB authoring/versioning, deflection search (Tracks A11, C11, D8)
- AI-assisted reply suggestions/auto-categorization/summarization (Track C12)
- Public API, outbound webhooks, API key management (Track C13)
- Mobile/PWA responsiveness, accessibility pass (Tracks C14, D12)
- Unified agent inbox, internal collaboration/@mentions/watchers (Tracks D1, D7)
- Multi-tenancy/white-labeling, billing/usage metering (Tracks D4, D10)
- Import/export tooling, GDPR right-to-be-forgotten, audit log retention (Tracks D5, D6, B8)
- Advanced/global search across tickets+KB+customers, full-text search infra (Tracks D9, B5)
- Load/chaos testing harness, capacity planning (Track D11)
- Object storage, Redis-backed rate limiting/idempotency, worker horizontal scaling, observability baseline (Tracks B2–B4, B6, B10)

Where a new feature below needs one of these (e.g., Change Management needs the approval-gate primitive from C10, or Incident Management needs the notification/real-time layer), it is called out under **Dependencies** rather than redesigned.

---

## 3. Major Missing Product Domains

### 3.1 Incident Management (major/critical incidents, distinct from routine tickets)
- **Problem:** The ticket model treats a P1 database outage affecting 500 users identically to one customer's password reset — same entity, same lifecycle, no concept of "many tickets, one incident," no incident commander role, no stakeholder communication channel, no timeline reconstruction after the fact.
- **Proposed capability:** A first-class `Incident` entity above tickets, with its own severity model, commander assignment, linked/impacted tickets, a structured timeline, and stakeholder broadcast channel.
- **Why missing:** The current data model has `ticket_links` for peer relationships between tickets, but nothing represents "N tickets are symptoms of one outage," and nothing models the incident-specific roles (commander, scribe) or the communication cadence major incidents require.
- **Business value:** This is the single highest-leverage addition for any org running production services — it's the difference between "a ticketing tool" and "what PagerDuty/Opsgenie/ServiceNow customers actually pay for."
- **Engineering value:** State machine design, aggregation/correlation logic, real-time broadcast, timeline event sourcing.
- **Dependencies:** Ticket linking (existing), notifications/real-time (C3), automation engine (B1) for correlation triggers.

### 3.2 Problem Management
- **Problem:** Recurring incidents get fixed symptomatically, ticket by ticket, with no mechanism to record the underlying root cause, track a workaround while the real fix is pending, or prevent recurrence.
- **Proposed capability:** `Problem` records with root-cause analysis, known-error tracking, and formal linkage from Incidents/Tickets → Problems → corrective actions.
- **Why missing:** No entity exists between "individual ticket" and "permanent fix"; there's nowhere to record "we know this happens, here's the workaround, here's the ticket to actually fix it."
- **Business value:** Reduces repeat-incident volume; is the ITIL-recognized differentiator between reactive and mature support orgs.
- **Engineering value:** Many-to-many relationship modeling (Problem ↔ Incidents ↔ Tickets), known-error searchable database.
- **Dependencies:** Incident Management (3.1), Task Management (3.6) for corrective action tracking.

### 3.3 Change Management
- **Problem:** The generic approval workflow (C10) is a boolean gate on a ticket transition. It cannot represent a change's risk classification, a scheduled maintenance window, a blackout-period conflict check, an implementation/rollback plan, or a change-caused-incident feedback loop — all of which are structurally different from "does this ticket need sign-off before closing."
- **Proposed capability:** A `ChangeRequest` domain object with its own risk-scored lifecycle (standard/normal/emergency change types), calendar-aware scheduling, and a bidirectional link to the incidents it causes or resolves.
- **Why missing:** No entity supports "this work is scheduled to happen at a specific time, in a specific window, with a plan for failure," which is fundamentally a scheduling + risk problem, not an approval problem.
- **Business value:** Change-caused outages are a top-3 cause of incidents in most orgs; formal change management with success-rate tracking is a core enterprise ITSM requirement (and often a compliance requirement, e.g., SOC 2 change control).
- **Engineering value:** Calendar conflict detection, risk-scoring rules, change→incident correlation analytics.
- **Dependencies:** Workflow Orchestration engine (3.11) for multi-stage approval-by-risk-tier, Incident Management (3.1) for correlation.

### 3.4 Asset / CMDB & Service Dependency Mapping
- **Problem:** There is no representation of *what* is being supported — no hardware, software, licenses, or the relationships between them and users, tickets, or services. Every ticket exists in a vacuum with no context about the affected system's ownership, warranty, or blast radius.
- **Proposed capability:** A Configuration Management Database: `Asset`/`ConfigurationItem` records with type-specific attributes, ownership, lifecycle state, and a relationship graph (depends-on, hosted-on, part-of) linking assets to services and to tickets/incidents.
- **Why missing:** Nothing in the data model represents inventory or infrastructure; tickets reference only tenant/user/organization, never "which server/laptop/license."
- **Business value:** Enables impact analysis ("if this asset goes down, which services/customers are affected"), warranty/license expiry tracking, and is table stakes for enterprise IT service management.
- **Engineering value:** Graph-shaped relational modeling, dependency traversal, polymorphic attribute schemas per asset type.
- **Dependencies:** Service Catalog (3.5) for the "asset supports service" edge; standalone otherwise.

### 3.5 Service Catalog & Request Fulfillment
- **Problem:** "Ticket" is used for both *something is broken* (incident) and *I need something* (a laptop, software access, a new hire's accounts) — with no service-specific request forms, no defined fulfillment steps, and no way for customers to browse "what can I ask for" rather than free-typing a title/description.
- **Proposed capability:** A `Service` catalog (owned services with defined offerings) feeding `ServiceRequest` types with structured, service-specific intake forms and multi-step fulfillment workflows (e.g., access request → manager approval → provisioning task → verification).
- **Why missing:** The current ticket creation form is generic (title/description/priority/category); there's no concept of a request *type* with its own schema, approver, and fulfillment steps.
- **Business value:** This is the #1 ticket-volume driver in most IT shops (password resets, access requests, hardware/software requests dwarf true incidents) — a real catalog dramatically improves self-service completion rates and reduces agent handling time.
- **Engineering value:** Dynamic form schema modeling, catalog-to-fulfillment-workflow binding, service ownership model.
- **Dependencies:** Workflow Orchestration engine (3.11) for fulfillment steps, Custom Fields (existing, C9) as the form-schema primitive to extend rather than duplicate, Asset/CMDB (3.4) for provisioning outputs.

### 3.6 Work / Task Management (sub-ticket work units)
- **Problem:** A ticket is atomic — there's no way to break "onboard new employee" into parallel/sequential sub-tasks (create AD account, order laptop, assign badge), assign each to a different owner, or block a ticket's resolution on incomplete sub-work.
- **Proposed capability:** `Task` entities as children of Tickets/ChangeRequests/ServiceRequests, with dependency ordering (sequential/parallel), individual assignment and due dates, checklists, and templates for recurring work breakdowns.
- **Why missing:** No child-work entity exists; the ticket model is flat.
- **Business value:** Essential for any multi-step fulfillment (onboarding, change implementation, incident remediation) and for team leads to see granular in-flight work.
- **Engineering value:** DAG-style dependency modeling for task ordering, template instantiation.
- **Dependencies:** Feeds Change Management (3.3), Request Fulfillment (3.5), and Incident Management (3.1) — build this first among the domain features since three other tracks consume it.

### 3.7 Customer Contract & Entitlement Management
- **Problem:** SLA policies (existing) are priority-based and tenant-wide. There is no concept of a customer having a *support contract* with a defined term, a bucket of prepaid support hours, or entitlement consumption tracking — the "premium tier gets tighter SLA" idea mentioned in D2 has nowhere to actually live as a governed, expiring commercial object.
- **Proposed capability:** `Contract`/`Entitlement` records per organization: term dates, support-hour allotments, entitled SLA policy overrides, and consumption tracking against the allotment, with expiry/renewal alerts.
- **Why missing:** `sla_policies` are global per-tenant, not customer-specific commercial commitments; there's no entity representing "this customer paid for X."
- **Business value:** Directly monetizable for MSPs/vendors who sell support tiers; prevents over-servicing customers past their contracted entitlement and provides renewal pipeline visibility.
- **Engineering value:** Time-boxed entitlement consumption accounting, contract-to-SLA-override resolution logic.
- **Dependencies:** Organizations (existing), SLA policies (existing) — this augments, not duplicates, D2's business-hours calendars (calendars are *when*, entitlements are *how much and at what tier*).

### 3.8 Workforce Management
- **Problem:** Assignment (existing/Track C7) only knows "who is active staff" and "who has fewest open tickets." It has no concept of an agent's skills, current shift/availability, or capacity ceiling — a Spanish-speaking billing specialist and a Tier-1 hardware agent are interchangeable to the router today.
- **Proposed capability:** Agent skill profiles, shift schedules, real-time availability status, and skill-based routing that extends the existing queue assignment modes rather than replacing them.
- **Why missing:** No `agent_skills`, `shifts`, or `availability` concept exists; routing is purely load-based.
- **Business value:** Higher first-contact resolution, correct routing for specialized/regulated work (e.g., only certified agents handle payment data).
- **Engineering value:** Constraint-based matching algorithm, shift-aware capacity forecasting.
- **Dependencies:** Extends Track C7's assignment modes (`skill_based` becomes a third `assignment_mode`); does not duplicate it.

### 3.9 Quality Assurance
- **Problem:** There's no mechanism to review whether resolved tickets were handled well — CSAT (existing) captures the *customer's* opinion, not a supervisor's structured evaluation against a rubric (tone, accuracy, policy adherence, resolution time).
- **Proposed capability:** Configurable QA scorecards, sampling rules (e.g., "review 10% of closed tickets, 100% of P1s"), supervisor review workflow, and coaching notes tied to agent performance history.
- **Why missing:** No scorecard/review entity exists; the closest is CSAT, which is customer-facing and unstructured for internal quality purposes.
- **Business value:** Standard requirement for any support org with a coaching/performance program; differentiates from CSAT-only quality signals.
- **Engineering value:** Configurable rubric schema, statistical sampling logic, aggregation into agent scorecards.
- **Dependencies:** Workforce Management (3.8) for tying scores to agent profiles; standalone otherwise.

### 3.10 Security Operations Extensions
- **Problem:** There's no differentiated handling for tickets/incidents involving sensitive data exposure, privileged access requests, or security events — they flow through the same pipeline as a password reset, with no PII-detection safeguard, no mandatory higher-approval gate, and no evidence-preservation requirement.
- **Proposed capability:** A `SecurityIncident` sub-classification with mandatory escalation routing, an optional PII-detection scan on ticket/comment content flagging likely-sensitive data for redaction review, and an evidence-attachment mode with tamper-evident (hash-chained) storage.
- **Why missing:** No content-scanning or differentiated-handling path exists for security-sensitive content today.
- **Business value:** Reduces breach/compliance exposure; often required for SOC 2 / ISO 27001 alignment.
- **Engineering value:** Content-scanning pipeline (pattern/NER-based), hash-chain evidence integrity, privileged-workflow gating.
- **Dependencies:** Incident Management (3.1) as the base entity; Workflow Orchestration (3.11) for mandatory-approval gates.

### 3.11 Workflow Orchestration Engine (cross-cutting)
- **Problem:** The automation engine (B1) is trigger→condition→action on ticket events — good for reactive rules, structurally unable to express "wait 2 hours, then if still unapproved escalate, then on approval run 3 parallel tasks, then on all-complete transition state" which Change Management, Request Fulfillment, and multi-step Incident remediation all need.
- **Proposed capability:** A general-purpose workflow engine supporting sequential/parallel branches, timers/wait states, human approval gates, reusable/versioned workflow definitions, and durable execution history with failure/compensation handling — used as the shared execution substrate for Change, Request Fulfillment, and Task orchestration rather than each domain hand-rolling its own state machine.
- **Why missing:** Nothing beyond the simple automation rule model exists; without this, Change/Request Fulfillment would each need bespoke, non-reusable orchestration code.
- **Business value:** Directly enables three of the domains above; is the kind of infrastructure investment that lets future request types/change types be defined declaratively instead of coded.
- **Engineering value:** This is the single deepest engineering artifact in this plan — durable execution, compensation, versioning.
- **Dependencies:** None (foundational); consumed by 3.3, 3.5, 3.6.

### 3.12 Event-Driven Architecture (cross-cutting)
- **Problem:** Track C13's webhooks are "call a URL when X happens" — fire-and-forget, no delivery guarantee, no internal consumer model. The domains above (Incident correlation, Problem linkage, Change→Incident correlation, Workflow engine triggers) all need *reliable internal* event propagation, which webhooks don't provide.
- **Proposed capability:** A domain event backbone using the transactional outbox pattern: events are written atomically with the state change, a relay publishes them to internal consumers (and, downstream, to the existing webhook dispatcher) with retry, dead-lettering, and replay for debugging/rebuilding read models.
- **Why missing:** No outbox table or internal event bus exists; automation triggers today are called synchronously inline, not via a durable event log.
- **Business value:** Reliability foundation — prevents "the automation didn't fire because the process crashed mid-request" class of bugs, and is a prerequisite for accurate incident timelines and change-correlation analytics.
- **Engineering value:** Outbox pattern, at-least-once delivery with idempotent consumers, dead-letter handling, event schema versioning.
- **Dependencies:** None (foundational); underpins 3.1, 3.2, 3.3, 3.11.

### 3.13 DevOps / Monitoring-Triggered Incidents
- **Problem:** Incidents in real operations are usually machine-detected (an alert fires), not agent-typed. There's no inbound path for a monitoring/alerting system to open and correlate an incident automatically.
- **Proposed capability:** An inbound alert-ingestion endpoint (generic webhook receiver + adapters for common formats) that creates/correlates Incidents, deduplicates repeat alerts for the same underlying issue, and links to the triggering Change if one is in-flight — implementing the flow *Monitoring Alert → Incident → Assignment → Change Correlation → Resolution*.
- **Why missing:** All current ticket-creation paths (web, API key, email) are human- or system-of-record-initiated, none are alert-shaped (no dedup/correlation semantics).
- **Business value:** Closes the loop between "the platform this system supports" and "the system that supports the platform" — a strong engineering/product differentiator.
- **Engineering value:** Deduplication/correlation heuristics, adapter pattern for heterogeneous alert payloads, idempotent ingestion.
- **Dependencies:** Incident Management (3.1), Event-Driven Architecture (3.12), Change Management (3.3) for correlation.

### 3.14 Intelligent Operations / Advanced AI (beyond Track C12)
- **Problem:** Track C12 covers reply suggestions, auto-categorization, and summarization — all *content-generation* assistance on a single ticket. None of it looks across tickets/incidents to predict or correlate.
- **Proposed capability:** Cross-entity intelligence: predictive SLA-breach risk scoring, duplicate/similar-incident detection via embedding similarity, and automatic post-incident-review draft generation from the incident timeline.
- **Why missing:** Requires the Incident/Problem domain objects and event history this plan introduces; couldn't exist before them regardless of AI capability.
- **Business value:** Meaningfully reduces MTTR and repeat-incident rate; a strong "AI infrastructure" portfolio signal beyond chatbot-style features.
- **Engineering value:** Embedding-based similarity search, feature-based risk scoring, autonomy-tiered AI feature classification (see 5.14).
- **Dependencies:** Incident Management (3.1), Event-Driven Architecture (3.12) for the timeline data these features consume.

**Explicitly excluded from Section 3** (considered, rejected as overlapping existing scope): a second "advanced search," a second "webhooks" system, a second "custom fields" mechanism, a second generic "approval workflow," and a second "role dashboard" — Sections 3.5's request forms reuse C9's custom-field primitive, 3.3/3.5's approvals reuse 3.11's engine (not C10's simple gate, but built as a superset so C10 usage keeps working), and 3.1–3.9's supervisor/agent views are additions to D3's dashboards, not new dashboard infrastructure.

---

## 4. Feature Tracks

- **Track E — Incident Management**
- **Track F — Problem Management**
- **Track G — Change Management**
- **Track H — Asset / CMDB**
- **Track I — Service Catalog & Request Fulfillment**
- **Track J — Work / Task Management**
- **Track K — Contract & Entitlement Management**
- **Track L — Workforce Management**
- **Track M — Quality Assurance**
- **Track N — Workflow Orchestration Engine** *(cross-cutting foundation)*
- **Track O — Event-Driven Architecture** *(cross-cutting foundation)*
- **Track P — Security Operations**
- **Track Q — DevOps / Monitoring Integration**
- **Track R — Advanced AI Operations**

Tracks N and O are foundational and are built first; every other track either consumes them directly or benefits from them.

---

## 5. Detailed Feature Specifications

### Track N — Workflow Orchestration Engine

**Purpose:** Provide a durable, reusable execution substrate for any multi-step process (change implementation, request fulfillment, incident remediation) so that Tracks G, I, and J don't each hand-roll bespoke state machines.

**User Problem:** Supervisors and admins need to define — without a code deploy — processes like "on emergency change creation, require CAB approval within 1 hour or auto-escalate; on approval, run implementation task, wait for verification, then close," and have the system durably execute that even across process restarts.

**Functional Requirements:**
- Define a `WorkflowDefinition` as a directed graph of steps: `action` (run a task/side-effect), `approval` (human gate), `timer` (wait N minutes/until timestamp), `branch` (conditional split on workflow variables), `parallel` (fan-out/fan-in), `webhook_call` (invoke external system, reuses C13 dispatcher).
- Workflow instances (`WorkflowRun`) carry a variable bag (JSON-typed key/value) seeded at start and mutated by steps.
- Definitions are versioned; in-flight runs continue on the version they started with, new runs use the latest published version.
- Runs support pause/resume (e.g., external timer step) and compensation (a step can declare a compensating action run if a later step fails, e.g., "revert access grant if provisioning task fails").
- Full execution history per run: every step transition, actor (system/user), timestamp, and variable diff.

**Backend Requirements:**
- `WorkflowEngineService`: `start_run(definition_id, context) -> run_id`, `advance(run_id, event)`, `get_state(run_id)`.
- Step execution is driven by consuming domain events (Track O) — e.g., a `change_request.approved` event advances any run waiting on an approval step for that change.
- Timer steps are backed by the existing job queue (`jobs` table, extended with a `workflow_timer` job type) rather than a new scheduler.
- Idempotent step execution: each step execution is keyed by `(run_id, step_id, attempt)` to make replay-safe.

**Frontend Requirements:**
- Admin: visual (or structured JSON-with-preview) workflow definition editor; list of published definitions with version history.
- Supervisor/Agent: a "workflow status" panel on any entity with an active run — current step, elapsed time, pending approvals with inline approve/reject.
- Run history/timeline view (reused by Track E's incident timeline UI).

**Database/Data Model Changes:**
- `workflow_definitions` (id, tenant_id, name, version, graph_json, status[draft/published/archived], created_by)
- `workflow_runs` (id, definition_id, definition_version, entity_type, entity_id, status[running/waiting/completed/failed/compensating], variables_json, started_at, completed_at)
- `workflow_run_steps` (id, run_id, step_key, step_type, status, input_json, output_json, started_at, completed_at, actor_id)
- `workflow_run_events` (id, run_id, event_type, payload_json, created_at) — append-only history

**API Changes:**
- `POST /workflows/definitions`, `PATCH /workflows/definitions/{id}` (publish new version)
- `POST /workflows/runs` (internal/service-initiated, not typically end-user)
- `GET /workflows/runs/{id}`, `GET /workflows/runs/{id}/history`
- `POST /workflows/runs/{id}/approvals/{step_id}` `{decision, comment}`

**Background Jobs / Events:** Consumes domain events to advance runs; emits `workflow.step_completed`, `workflow.run_completed`, `workflow.run_failed`. Timer steps enqueue `workflow_timer` jobs picked up by the existing worker poll loop.

**Authorization / Permissions:** New `workflow.manage` (define/publish), `workflow.approve` (act on approval steps assigned to the user's role/queue).

**Audit Requirements:** Every step transition and approval decision audited with actor and reason.

**Notifications:** Approval-pending steps notify the assigned approver(s); run failures notify the definition owner/admin.

**Testing Requirements:** State-machine transition tests per step type; concurrency tests (two approvals racing); failure/compensation tests; timer-step tests using a fake clock; idempotent-replay tests.

**Observability:** Metrics: runs started/completed/failed by definition, average step duration, approval wait time. Trace spans per step execution.

**Dependencies:** Event-Driven Architecture (Track O) for event-driven step advancement; existing job queue for timers.

**Technical Complexity:** High.

**Engineering Concepts Demonstrated:** Workflow orchestration, durable execution, idempotency, compensation/saga pattern, versioning, state machines.

**Acceptance Criteria:**
- A published workflow definition with an approval step blocks progression until an authorized user approves via API/UI.
- Killing and restarting the worker mid-run resumes the run from its last completed step with no duplicate side effects (verified by idempotency key test).
- A step configured with a compensating action executes that action when a downstream step fails.
- Definition v2 published while a v1 run is in flight does not alter the in-flight run's behavior.

---

### Track O — Event-Driven Architecture

**Purpose:** Give the platform a reliable internal event backbone so incident correlation, problem linkage, workflow advancement, and analytics all consume the same durable, ordered event stream instead of ad hoc synchronous calls.

**User Problem (indirect/infrastructural):** Without this, features like "auto-correlate this new ticket with the open incident" or "advance the workflow when a change is approved" are either missed on crash/retry, or require every feature to re-implement its own reliable-delivery logic.

**Functional Requirements:**
- Every significant state change (ticket created/status changed, incident opened/updated, change approved, task completed, etc.) writes a domain event **in the same DB transaction** as the state change (transactional outbox).
- A relay process polls the outbox and publishes to registered internal consumers (workflow engine, correlation engine, analytics projector) and, for events flagged externally-visible, to the existing webhook dispatcher (Track C13) — Track O becomes C13's internal event source rather than a competing system.
- Consumers are idempotent (dedup by `event_id`); failed consumer processing retries with backoff, then dead-letters after N attempts.
- Events are replayable by time range or entity, for debugging and for rebuilding derived read models (e.g., regenerating an incident timeline).

**Backend Requirements:**
- `outbox_events` table written via a shared `emit_event()` helper called from service-layer code at the same transaction boundary as the state mutation (no separate "publish" step that can be skipped).
- `EventRelay` worker extension (runs in the existing worker process as a new job type or dedicated loop) — polls `outbox_events` with `SKIP LOCKED`, dispatches to consumers, updates delivery status.
- `event_consumers` registry (in code, not DB) mapping event type → consumer handlers; `event_deliveries` table tracks per-consumer delivery status for retry/dead-letter.

**Frontend Requirements:**
- Admin "Event Log" viewer (filter by entity/type/date) — mainly an observability/debugging tool, gated by a new `event.view` permission.
- Dead-letter queue admin view with manual "retry" action.

**Database/Data Model Changes:**
- `outbox_events` (id, tenant_id, event_type, entity_type, entity_id, payload_json, schema_version, created_at, published_at)
- `event_deliveries` (id, event_id, consumer_name, status[pending/delivered/failed/dead_letter], attempts, last_error, updated_at)
- Index on `outbox_events(published_at)` for relay polling; index on `(entity_type, entity_id)` for replay-by-entity.

**API Changes:**
- `GET /events?entity_type=&entity_id=&from=&to=` (admin/debug)
- `GET /events/dead-letter`, `POST /events/dead-letter/{id}/retry`
- No public-facing API changes beyond what C13 already exposes (webhooks) — this is the reliable producer behind that existing surface.

**Background Jobs / Events:** This *is* the events/jobs layer for everything else in this document — see per-track "producer/consumer" tables in Section 9.

**Authorization / Permissions:** `event.view` (read event log), `event.admin` (retry dead letters).

**Audit Requirements:** Dead-letter retries are audited (who retried, which event).

**Notifications:** Optional alert (existing notification channel) to admins when the dead-letter queue exceeds a threshold.

**Testing Requirements:** Outbox-write-is-transactional test (rollback the business transaction, assert no event persisted); at-least-once delivery test with a deliberately-failing consumer; idempotent-consumer replay test; dead-letter-after-N-attempts test; ordering test within a single entity's event stream.

**Observability:** Metrics: events emitted/sec by type, relay lag (time from `created_at` to `published_at`), dead-letter queue depth, per-consumer failure rate. Alert on relay lag exceeding threshold (indicates worker falling behind).

**Dependencies:** None (foundational). Existing worker process and `jobs`/`SKIP LOCKED` pattern extended, not replaced.

**Technical Complexity:** High.

**Engineering Concepts Demonstrated:** Transactional outbox pattern, at-least-once delivery, idempotent consumers, dead-letter handling, event schema versioning, distributed-systems reliability.

**Acceptance Criteria:**
- A state change that fails after the DB transaction commits but before the relay publishes is still delivered (no event loss) after worker restart.
- A state change whose DB transaction rolls back produces zero delivered events.
- A consumer that throws on every attempt results in the event reaching `dead_letter` status after the configured retry count, not an infinite loop.
- Replaying events for a given `entity_id` reproduces the same sequence of consumer calls as the original delivery (verified in a test harness).

---

### Track E — Incident Management

**Purpose:** Model major/service-impacting incidents as first-class objects distinct from routine tickets, with correlation, commander assignment, timeline, and stakeholder communication.

**User Problem:** When a service-impacting event occurs, agents currently open unrelated tickets with no shared context, no single owner coordinating response, and no record of what was tried and when — making post-incident review reconstruction manual and unreliable.

**Functional Requirements:**
- Create an `Incident` (manually or via Track Q's alert ingestion) with severity (SEV1–SEV4), affected services (links to Track I's Service Catalog), and status lifecycle: `DETECTED → INVESTIGATING → IDENTIFIED → MONITORING → RESOLVED → CLOSED` (distinct from the ticket lifecycle — incidents track *service* impact, not individual work item state).
- Assign an Incident Commander (and optionally a Scribe) — roles, not just an assignee.
- Link any number of existing Tickets to an Incident (`impacted_by` relationship); tickets keep their own lifecycle independently.
- Structured, append-only Timeline: system-generated entries (status changes, links added, correlated events from Track O) interleaved with commander-authored freeform updates.
- Stakeholder communication: a broadcast update posted to the timeline can be flagged "customer-visible," which publishes it to a public incident status feed (consumed by the customer portal / status page) — content authored once, distributed to both audiences.
- Duplicate/similar-incident detection: on creation, surface open incidents with overlapping affected services or similar title/description (exact-match on affected service is deterministic; textual similarity is an **[Assumed]** later enhancement under Track R).
- Post-incident review: on `CLOSED`, prompt for a structured PIR (impact summary, root cause if known, action items) which creates linked Problem records (Track F) for follow-up.

**Backend Requirements:**
- `IncidentService`: create/update/transition, `link_ticket`, `assign_commander`, `add_timeline_entry`, `close_with_pir`.
- State machine enforced server-side, mirroring the ticket lifecycle's pattern (allowed-transitions-by-role) but as its own definition.
- Correlation check on creation queries open incidents by affected-service overlap (simple, indexed query — not ML in v1).

**Frontend Requirements:**
- Incident list view (filterable by severity/status/service), separate from the ticket list.
- Incident detail page: header (severity, status, commander, affected services), linked-tickets panel with "link existing ticket" action, timeline feed with an update-composer (customer-visible toggle), and a PIR form on close.
- A public, unauthenticated incident status view (customer-visible timeline entries only) — new route, reuses the existing customer-portal styling.

**Database/Data Model Changes:**
- `incidents` (id, tenant_id, title, severity, status, commander_id, scribe_id, detected_at, resolved_at, closed_at, created_by, source[manual/alert])
- `incident_services` (incident_id, service_id) — M:N to Track I's `services`
- `incident_tickets` (incident_id, ticket_id, relationship[impacted_by/related])
- `incident_timeline_entries` (id, incident_id, entry_type[status_change/comment/system_event], body, is_customer_visible, author_id, created_at)
- `post_incident_reviews` (id, incident_id, impact_summary, root_cause_summary, action_item_count, completed_by, completed_at)

**API Changes:**
- `POST /incidents`, `GET /incidents`, `GET /incidents/{id}`, `POST /incidents/{id}/transitions`
- `POST /incidents/{id}/link-ticket`, `DELETE /incidents/{id}/link-ticket/{ticket_id}`
- `POST /incidents/{id}/timeline`, `GET /incidents/{id}/timeline`
- `POST /incidents/{id}/pir`
- `GET /public/incidents/{id}/status` (unauthenticated, customer-visible entries only)

**Background Jobs / Events:** Emits `incident.opened`, `incident.status_changed`, `incident.ticket_linked`, `incident.closed`. Consumes `ticket.created` (for correlation surfacing, not auto-linking) and, from Track Q, `alert.received`.

**Authorization / Permissions:** New `incident.view`, `incident.manage` (create/update), `incident.command` (assign self/others as commander — typically supervisor+), reuse `ticket.view` for linked-ticket visibility checks.

**Audit Requirements:** All state transitions, commander assignment changes, and PIR completion audited.

**Notifications:** Commander assignment notifies the assignee; customer-visible timeline updates notify watchers/subscribed contacts on affected organizations; SEV1 creation notifies on-call/supervisor role (integrates with Track L's schedule once available, degrades to "all supervisors" until then).

**Testing Requirements:** State-machine transition tests; correlation-detection tests (overlapping vs. non-overlapping services); customer-visible filtering tests (ensure internal-only entries never reach the public endpoint); PIR-creates-problem-record integration test.

**Observability:** Metrics: incidents opened/closed by severity, mean time to detect/acknowledge/resolve (MTTD/MTTA/MTTR), open-incident count by severity (dashboard widget). Alert on SEV1 open > threshold duration.

**Dependencies:** Event-Driven Architecture (Track O); Service Catalog (Track I) for affected-services linkage (can ship with a simple free-text service tag if Track I isn't yet built, upgraded later — **[Assumed]** fallback).

**Technical Complexity:** High.

**Engineering Concepts Demonstrated:** Independent state machine design, event correlation, append-only timeline (event-sourcing-flavored), dual-audience content publishing, cross-domain linkage.

**Acceptance Criteria:**
- Creating an incident with an affected service that overlaps an open incident surfaces that incident as a suggested duplicate before save.
- A timeline entry marked customer-visible appears on the public status endpoint; a non-visible entry does not.
- Transitioning an incident to CLOSED without completing the PIR form is blocked for SEV1/SEV2 (configurable), allowed for SEV3/SEV4.
- Closing an incident with a PIR that specifies a root cause creates a linked `Problem` record with `origin_incident_id` set.

---

### Track F — Problem Management

**Purpose:** Track root causes and known errors across recurring incidents so fixes are permanent rather than repeated symptomatic patches.

**User Problem:** The same underlying defect causes repeat incidents/tickets because there's nowhere to record "we've seen this, here's the known workaround, here's the actual fix in progress."

**Functional Requirements:**
- `Problem` records with lifecycle: `NEW → INVESTIGATING → KNOWN_ERROR → FIX_IN_PROGRESS → RESOLVED → CLOSED`.
- Link Problems to originating Incident(s) and to any number of Tickets exhibiting the same symptom.
- `KNOWN_ERROR` status makes the problem (with its workaround text) searchable/surfaceable to agents triaging a new ticket with matching symptoms (surfaced as a suggestion on ticket creation, similar to KB deflection).
- Corrective/preventive action tracking via linked Tasks (Track J) — "the real fix" is a trackable task, not just a status.
- Recurring-incident detection: flag when N incidents link to the same service within a rolling window without an associated Problem — nudges creation of a Problem record.

**Backend Requirements:**
- `ProblemService`: create/update/transition, `link_incident`, `link_ticket`, `mark_known_error(workaround_text)`.
- Recurrence check: scheduled job (reuses worker loop) scanning incidents-by-service over a rolling window, flagging clusters without a linked problem.

**Frontend Requirements:**
- Problem list/detail pages mirroring Incident's structure (linked incidents, linked tickets, workaround text, corrective-action tasks).
- "Known error" banner surfaced on ticket-creation form when title/category matches a known-error problem (reuses existing KB-deflection UI pattern from C11).

**Database/Data Model Changes:**
- `problems` (id, tenant_id, title, status, root_cause, workaround, origin_incident_id, created_by, resolved_at, closed_at)
- `problem_incidents` (problem_id, incident_id)
- `problem_tickets` (problem_id, ticket_id)
- `problem_actions` (problem_id, task_id) — links to Track J tasks

**API Changes:**
- `POST /problems`, `GET /problems`, `GET /problems/{id}`, `POST /problems/{id}/transitions`
- `POST /problems/{id}/link-incident`, `POST /problems/{id}/link-ticket`
- `GET /problems/known-errors?q=` (search known-error workarounds, used by ticket-creation suggestion)

**Background Jobs / Events:** Emits `problem.created`, `problem.known_error_published`, `problem.resolved`. Consumes `incident.closed` (for recurrence-window scanning) and `pir.completed` (auto-create from PIR, per Track E).

**Authorization / Permissions:** `problem.view`, `problem.manage`.

**Audit Requirements:** State transitions and known-error publication audited.

**Notifications:** Recurrence-detection flags notify supervisors; known-error publication notifies agents currently assigned to open tickets matching the symptom (best-effort keyword match).

**Testing Requirements:** State-machine tests; recurrence-detection window tests (boundary conditions); known-error search relevance tests.

**Observability:** Metrics: open problems by status, mean time to known-error, recurring-incident rate before/after problem resolution (validates the feature's actual impact).

**Dependencies:** Track E (Incident Management), Track J (Task Management) for corrective actions.

**Technical Complexity:** Medium.

**Engineering Concepts Demonstrated:** Many-to-many domain linkage, scheduled recurrence-detection analytics, searchable knowledge surfacing.

**Acceptance Criteria:**
- Three incidents affecting the same service within a 7-day rolling window with no linked problem produce a supervisor notification.
- Marking a problem `KNOWN_ERROR` with workaround text makes it appear in `known-errors` search results.
- Creating a ticket whose title matches an active known-error's keywords surfaces the workaround before submission.

---

### Track G — Change Management

**Purpose:** Provide a real change-management domain — risk-scored, scheduled, plan-carrying — distinct from the generic ticket approval gate.

**User Problem:** Planned infrastructure/config changes today are either informal tickets or absent entirely from the system, so there's no visibility into what's scheduled, no blackout-period enforcement, and no data on which changes caused incidents.

**Functional Requirements:**
- `ChangeRequest` with type (`standard` — pre-approved template, `normal` — requires CAB approval, `emergency` — expedited approval) and lifecycle: `DRAFT → SUBMITTED → APPROVED/REJECTED → SCHEDULED → IN_PROGRESS → COMPLETED/FAILED → CLOSED`.
- Risk assessment: structured fields (impact scope, rollback complexity, affected services) feeding a computed risk score that determines the required approval path (standard changes with a pre-approved template skip CAB; normal/emergency route through Track N workflow with risk-tiered approver sets).
- Scheduling: proposed start/end window checked against configurable blackout periods and other scheduled changes on the same service (conflict warning, not hard block).
- Implementation plan and rollback plan as structured fields (not just free text — minimally: ordered steps, each optionally linked to a Task).
- On `COMPLETED`, record a success/failure outcome; on `FAILED` or if an Incident is opened referencing this change within a configurable window post-implementation, auto-link them for change→incident correlation reporting.

**Backend Requirements:**
- `ChangeService`: create/update, `submit_for_approval` (starts a Track N workflow run keyed to risk tier), `schedule`, `start_implementation`, `complete(outcome)`.
- Blackout/conflict check: query scheduled changes + configured blackout windows overlapping the proposed window and affected service.
- Change→incident correlation: on `incident.opened` (Track O event), check for changes to the same service(s) completed within the correlation window and surface as a candidate link (human-confirmed, not automatic).

**Frontend Requirements:**
- Change request form: type selector, risk-assessment fields (computed score shown live), affected services, scheduled window with calendar view showing existing changes/blackouts.
- Change calendar view (team/service filterable) — visual schedule of upcoming/in-progress changes.
- Change detail page: plan/rollback plan display, linked tasks, approval status (from Track N), correlated-incident panel.
- CAB approval queue view for approvers.

**Database/Data Model Changes:**
- `change_requests` (id, tenant_id, title, type, status, risk_score, risk_fields_json, requested_by, scheduled_start, scheduled_end, actual_start, actual_end, outcome)
- `change_services` (change_id, service_id)
- `change_plan_steps` (id, change_id, kind[implementation/rollback], sequence, description, task_id nullable)
- `blackout_periods` (id, tenant_id, name, start_at, end_at, service_id nullable, recurrence_rule nullable)
- `change_incident_links` (change_id, incident_id, link_type[caused/coincident], confirmed_by)

**API Changes:**
- `POST /changes`, `GET /changes`, `GET /changes/{id}`, `PATCH /changes/{id}`
- `POST /changes/{id}/submit`, `POST /changes/{id}/schedule`, `POST /changes/{id}/start`, `POST /changes/{id}/complete`
- `GET /changes/calendar?from=&to=&service_id=`
- `POST /blackout-periods`, `GET /blackout-periods`
- `POST /changes/{id}/link-incident`

**Background Jobs / Events:** Emits `change.submitted`, `change.approved`, `change.scheduled`, `change.completed`, `change.failed`. Consumes `workflow.run_completed` (approval outcome) and `incident.opened` (correlation surfacing).

**Authorization / Permissions:** `change.view`, `change.create`, `change.approve` (CAB), `change.implement`.

**Audit Requirements:** Full lifecycle audited, including risk score computation inputs (for later dispute/review) and correlation confirmations.

**Notifications:** Approvers notified on submission; requester notified on approve/reject; affected-service watchers notified on scheduling; supervisor notified on `FAILED` outcome.

**Testing Requirements:** Risk-scoring tests across boundary inputs; blackout-conflict detection tests; state-machine tests; standard-change-skips-CAB tests; correlation-window tests.

**Observability:** Metrics: change success rate, change volume by type/risk tier, changes causing incidents (%), average time-in-approval by risk tier.

**Dependencies:** Track N (Workflow Orchestration) for approval routing, Track J (Tasks) for plan steps, Track E (Incident) for correlation.

**Technical Complexity:** High.

**Engineering Concepts Demonstrated:** Risk-scoring rule engine, calendar/scheduling conflict detection, cross-domain correlation, workflow-engine consumption.

**Acceptance Criteria:**
- A `normal` change cannot reach `SCHEDULED` without a completed CAB approval workflow run.
- A `standard` change using a pre-approved template reaches `SCHEDULED` without a manual approval step.
- Proposing a schedule window overlapping a configured blackout period on the same service surfaces a conflict warning (non-blocking, requires acknowledgment).
- An incident opened within the correlation window referencing a service with a recently completed change surfaces that change as a suggested link.

---

### Track H — Asset / CMDB

**Purpose:** Represent the infrastructure and inventory the support organization is actually responsible for, and its relationships to services, users, and tickets.

**User Problem:** Agents and change/incident owners have no system record of what hardware/software/licenses exist, who owns them, or what depends on what — impact analysis is guesswork.

**Functional Requirements:**
- `Asset` (a.k.a. Configuration Item) records with a type (`hardware`, `software_license`, `service_instance`, `cloud_resource` — extensible enum), type-specific attributes (structured per type, not a single JSONB blob without schema — see data model note), owner (user or organization), lifecycle status (`in_use`, `in_stock`, `retired`, `disposed`), warranty/license expiry dates.
- Relationship graph: `depends_on`, `hosted_on`, `part_of` edges between assets, and `supports` edges from assets to Services (Track I).
- Asset-to-ticket linkage: a ticket can reference the affected asset(s); asset detail page shows ticket history.
- Expiry dashboard: upcoming warranty/license expirations within a configurable window.
- Basic dependency traversal: "if this asset is impacted, what depends on it" (transitive closure query, bounded depth) — feeds Incident impact assessment (Track E's affected-services determination, when the affected service is inferred from an affected asset rather than chosen directly).

**Backend Requirements:**
- `AssetService`: CRUD, `link_dependency`, `link_ticket`, `get_dependents(asset_id, max_depth)`.
- Dependency traversal implemented as a recursive CTE (Postgres) bounded by depth to avoid pathological graphs.

**Frontend Requirements:**
- Asset list (filterable by type/status/owner), asset detail page with attributes, relationship graph (simple list-based "depends on / depended on by," not necessarily a visual graph in v1), linked-ticket history, expiry badge.
- Expiry dashboard widget (admin/supervisor).
- "Link asset" action on ticket detail page.

**Database/Data Model Changes:**
- `assets` (id, tenant_id, name, asset_type, status, owner_user_id nullable, owner_org_id nullable, purchased_at, warranty_expires_at, license_expires_at, created_at)
- `asset_attributes` (asset_id, attribute_key, attribute_value) — EAV-style for type-specific fields, chosen over a single JSONB blob so attribute keys stay queryable/indexable per tenant; a `asset_type_attribute_schemas` table (asset_type, attribute_key, data_type, required) defines the expected schema per type for form rendering, with EAV storage remaining the source of truth
- `asset_relationships` (id, source_asset_id, target_asset_id, relationship_type[depends_on/hosted_on/part_of])
- `asset_services` (asset_id, service_id)
- `ticket_assets` (ticket_id, asset_id)

**API Changes:**
- `POST /assets`, `GET /assets`, `GET /assets/{id}`, `PATCH /assets/{id}`
- `POST /assets/{id}/relationships`, `GET /assets/{id}/dependents?depth=`
- `POST /tickets/{id}/link-asset/{asset_id}`
- `GET /assets/expiring?within_days=`

**Background Jobs / Events:** Emits `asset.created`, `asset.retired`, `asset.expiry_approaching` (scheduled scan). Consumed by Track E for asset-derived affected-service inference (optional enhancement) and by notification system for expiry alerts.

**Authorization / Permissions:** `asset.view`, `asset.manage`.

**Audit Requirements:** Ownership changes, status changes (especially retirement/disposal, for compliance), relationship changes.

**Notifications:** Expiry-approaching alerts to asset owner and admin.

**Testing Requirements:** Dependency traversal tests (cycles must not infinite-loop — enforce max depth and cycle detection), attribute-schema validation tests, expiry-scan boundary tests.

**Observability:** Metrics: asset count by type/status, expiring-soon count, orphaned-asset count (no owner).

**Dependencies:** Standalone for core CRUD; Service Catalog (Track I) for the `supports` edge; Track E benefits from it but doesn't require it.

**Technical Complexity:** Medium.

**Engineering Concepts Demonstrated:** Graph relationship modeling, recursive query traversal with cycle/depth safety, EAV schema-on-read modeling with a schema registry (deliberately not "just JSONB everywhere").

**Acceptance Criteria:**
- Creating a `depends_on` cycle (A depends on B depends on A) is rejected at write time.
- `GET /assets/{id}/dependents?depth=3` returns the correct transitive set for a known fixture graph and does not exceed the requested depth.
- An asset within the expiry window generates exactly one `asset.expiry_approaching` event (not one per scan run) — deduplicated per asset per expiry threshold crossing.

---

### Track I — Service Catalog & Request Fulfillment

**Purpose:** Give customers a structured way to request things (not just report problems), with service-specific forms and a defined fulfillment workflow, replacing the generic ticket-creation form for request-type work.

**User Problem:** Customers submitting "I need X" requests today fill the same free-text form as someone reporting an outage; there's no guided intake, no defined approver, and no visibility into fulfillment steps.

**Functional Requirements:**
- `Service` catalog: name, description, owner (user/team), status (`available`/`unavailable`), and one or more `RequestType`s it offers.
- Each `RequestType` defines a form schema (reusing the custom-field primitive from existing Track C9 rather than inventing a second schema system), a default fulfillment `WorkflowDefinition` (Track N), and an SLA target specific to that request type (distinct from ticket-priority SLA — e.g., "laptop requests: 3 business days" regardless of priority field).
- Customer-facing catalog browse page: services grouped/searchable, each showing its request types.
- Submitting a request creates a `ServiceRequest` (a specialization that still produces an underlying Ticket for unified inbox/reporting purposes — not a parallel silo) whose fulfillment is driven by the bound workflow (e.g., manager approval → provisioning task → verification → auto-close).
- Fulfillment task assignment surfaces on the assignee's task list (Track J).

**Backend Requirements:**
- `ServiceCatalogService`: CRUD on services/request types; `submit_request(request_type_id, form_data) -> service_request_id`, which creates the backing Ticket, attaches the request-type SLA, and starts the bound Track N workflow run.
- Form validation against the request type's field schema (reusing C9's custom-field validation logic).

**Frontend Requirements:**
- Customer portal: catalog browse/search page, request-type intake form (dynamically rendered from schema, same renderer as C9's custom fields), request status tracker (reuses ticket detail page, extended with a "fulfillment steps" panel sourced from the workflow run).
- Admin: catalog management (create/edit services and request types, bind workflow definitions, set request-type SLA).

**Database/Data Model Changes:**
- `services` (id, tenant_id, name, description, owner_team_id, status)
- `request_types` (id, service_id, name, custom_field_schema_id — FK into existing C9 schema table, workflow_definition_id, sla_target_hours)
- `service_requests` (id, ticket_id — 1:1 with existing tickets table, request_type_id, workflow_run_id)

**API Changes:**
- `POST /services`, `GET /services` (catalog), `POST /services/{id}/request-types`, `GET /services/{id}/request-types`
- `POST /service-requests` `{request_type_id, form_data}` → creates ticket + service_request + starts workflow
- `GET /service-requests/{id}` (includes fulfillment step status via joined workflow run)

**Background Jobs / Events:** Emits `service_request.submitted`, `service_request.fulfilled`. Consumes `workflow.run_completed` to auto-transition the backing ticket to RESOLVED on fulfillment workflow completion.

**Authorization / Permissions:** `catalog.manage` (admin), `service_request.view`/`create` (reuses `ticket.view_own`/`ticket.create` scoping since it's ticket-backed).

**Audit Requirements:** Catalog changes, request submissions, fulfillment completion.

**Notifications:** Requester notified at each fulfillment milestone (approval granted, provisioning started, completed); fulfillment task assignees notified per Track J/N norms.

**Testing Requirements:** Form-schema validation tests; ticket-and-workflow-created-atomically test (submission failure shouldn't leave an orphaned ticket without a request record or vice versa); fulfillment-completion auto-closes-ticket test.

**Observability:** Metrics: requests by type, average fulfillment time vs. SLA target, catalog page views vs. submissions (funnel).

**Dependencies:** Track N (Workflow Orchestration) for fulfillment steps, existing C9 custom fields for form schema, Track J for fulfillment tasks, Track H (Asset/CMDB) as a natural provisioning output (e.g., a "new laptop" request fulfillment step can create an Asset record — **[Assumed]** optional integration, not required for v1).

**Technical Complexity:** Medium-High.

**Engineering Concepts Demonstrated:** Schema reuse/composition across domains, workflow-engine consumption, transactional cross-entity creation, dynamic form rendering.

**Acceptance Criteria:**
- Submitting a request for a `RequestType` with a bound workflow creates exactly one Ticket, one ServiceRequest, and one WorkflowRun in a single transaction.
- The customer-facing status view shows the current fulfillment step name and reflects updates as the workflow advances.
- A request type's SLA target (not the ticket priority default) determines its due-date calculation.

---

### Track J — Work / Task Management

**Purpose:** Provide a reusable child-work-unit primitive consumed by Change, Request Fulfillment, and Incident remediation, so multi-step work has individual ownership, ordering, and completion tracking.

**User Problem:** There's no way to break a ticket/change/request into assignable, orderable sub-units of work with their own due dates and dependency constraints.

**Functional Requirements:**
- `Task` entities attachable to any parent entity type (`ticket`, `change_request`, `service_request`, `problem`) via a polymorphic parent reference.
- Ordering: tasks can declare `depends_on` other tasks within the same parent; dependent tasks are blocked from starting until dependencies complete (supports both sequential chains and parallel groups sharing a common downstream dependency).
- Checklist items within a task (lightweight, no independent assignment — just completion tracking) for granular steps that don't need their own owner.
- Task templates: a named, reusable set of tasks (with dependency structure) instantiated as a group (e.g., "new-hire onboarding" template creates 6 tasks with the right dependencies in one action) — used by Track I's fulfillment workflows and directly by supervisors.
- Task assignment, due dates, and status (`PENDING → IN_PROGRESS → BLOCKED → DONE → CANCELLED`).

**Backend Requirements:**
- `TaskService`: CRUD, `instantiate_template(template_id, parent) -> task_ids`, dependency-aware `can_start(task_id)` check, `complete(task_id)` which unblocks dependents and emits completion events consumed by Track N (workflow steps waiting on task completion) and Track G/I directly.

**Frontend Requirements:**
- Task panel embedded on parent entity detail pages (ticket/change/request/problem) — list with status, assignee, due date, dependency indicators (blocked-by).
- Personal "My Tasks" view (cross-parent-entity), naturally extending the existing unified-inbox concept (D1) rather than duplicating it.
- Template management screen (admin): define template + task list + dependencies.

**Database/Data Model Changes:**
- `tasks` (id, tenant_id, parent_type, parent_id, title, description, status, assignee_id, due_at, created_from_template_id nullable)
- `task_dependencies` (task_id, depends_on_task_id)
- `task_checklist_items` (id, task_id, label, is_done)
- `task_templates` (id, tenant_id, name)
- `task_template_items` (id, template_id, title, description, depends_on_template_item_id nullable)

**API Changes:**
- `POST /tasks`, `GET /tasks?parent_type=&parent_id=`, `PATCH /tasks/{id}`, `POST /tasks/{id}/complete`
- `POST /task-templates`, `POST /task-templates/{id}/instantiate` `{parent_type, parent_id}`
- `GET /my-tasks` (assignee-scoped, cross-parent-type)

**Background Jobs / Events:** Emits `task.completed`, `task.blocked_cleared`. Consumed by Track N (approval/action steps that represent "a task must complete") and Track G/I directly for progress display.

**Authorization / Permissions:** `task.view`, `task.manage` (create/assign), individual assignees can always update their own task's status.

**Audit Requirements:** Assignment changes, status changes, template instantiations.

**Notifications:** Assignment notification; "unblocked" notification when a dependency completes and the task becomes startable.

**Testing Requirements:** Dependency-cycle rejection tests; unblock-on-completion tests; template instantiation produces correctly-wired dependency graph tests; polymorphic-parent scoping tests (a task query for parent A never returns parent B's tasks).

**Observability:** Metrics: tasks completed/day, average task age by parent type, blocked-task count (backlog health signal).

**Dependencies:** None (foundational within the domain layer); consumed by Tracks F, G, I.

**Technical Complexity:** Medium.

**Engineering Concepts Demonstrated:** Polymorphic association modeling, DAG dependency resolution, template/instantiation pattern.

**Acceptance Criteria:**
- A task with an incomplete dependency cannot be transitioned to `IN_PROGRESS` (API rejects with a clear error).
- Completing a task automatically clears the block on any solely-dependent task and fires a notification to its assignee.
- Instantiating a template with a 3-step sequential + 2-step parallel structure produces exactly the expected dependency edges (covered by a fixture-based test).

---

### Track K — Contract & Entitlement Management

**Purpose:** Represent commercial support commitments per customer organization — term, entitled hours, SLA overrides — as governed, expiring objects distinct from tenant-wide SLA policies.

**User Problem:** There's no way to know whether a customer is in-contract, how much support they've consumed against an allotment, or when their entitlement expires, so premium-tier commitments can't be enforced or reported on.

**Functional Requirements:**
- `Contract` per organization: term (start/end), plan tier, entitled support-hour allotment (nullable for unlimited), SLA policy override (references existing `sla_policies`, if the contract tier requires tighter targets than the tenant default).
- Entitlement consumption tracking: time logged against tickets belonging to the contracted organization accrues against the allotment (requires basic time-tracking on ticket work — **[New, minimal scope]**: a `time_entries` table capturing agent-logged minutes per ticket, intentionally minimal — full timesheet/billing functionality is out of scope here and left to Track D10 if built).
- Expiry/renewal alerts at configurable thresholds (e.g., 30/7 days before term end, or 80%/100% of hour allotment consumed).
- When a contract's SLA override is active, ticket creation for that organization uses the override policy instead of the tenant-default priority-based policy.

**Backend Requirements:**
- `ContractService`: CRUD, `log_time(ticket_id, minutes)`, `get_consumption(contract_id)`, `check_thresholds()` (scheduled scan).
- SLA-attachment logic (existing, in ticket creation) extended with a lookup: "does the requester's organization have an active contract with an SLA override? use it; else fall back to tenant default."

**Frontend Requirements:**
- Admin: contract CRUD per organization, consumption dashboard (hours used/remaining, days to expiry).
- Agent: quick time-log widget on ticket detail (minutes spent), visible when the ticket's organization has an active contract.
- Renewal pipeline view (contracts expiring within N days, admin-facing).

**Database/Data Model Changes:**
- `contracts` (id, tenant_id, organization_id, plan_tier, start_at, end_at, entitled_hours nullable, sla_policy_override_id nullable, status[active/expired/cancelled])
- `time_entries` (id, ticket_id, contract_id nullable, agent_id, minutes, logged_at, note)
- Index on `contracts(organization_id, status)` for the SLA-lookup hot path.

**API Changes:**
- `POST /contracts`, `GET /contracts`, `PATCH /contracts/{id}`
- `POST /tickets/{id}/time-entries`, `GET /contracts/{id}/consumption`
- `GET /contracts/expiring?within_days=`

**Background Jobs / Events:** Emits `contract.threshold_reached`, `contract.expired` (scheduled scan, reuses worker loop). Consumed by notification system.

**Authorization / Permissions:** `contract.view`, `contract.manage`; time-entry logging permitted to any agent with `ticket.update` on the ticket.

**Audit Requirements:** Contract creation/changes, especially SLA overrides (commercial impact); time-entry corrections.

**Notifications:** Threshold/expiry alerts to account owner (admin) and, optionally, the customer's escalation contact.

**Testing Requirements:** SLA-override-takes-precedence test; consumption-calculation accuracy tests; expiry-scan boundary tests; contract-expired-falls-back-to-tenant-default test.

**Observability:** Metrics: active contracts by tier, aggregate consumption vs. entitlement, renewal-pipeline value (if plan tiers carry a nominal value — **[Assumed]** optional field).

**Dependencies:** Organizations (existing), SLA policies (existing). Independent of Tracks E–J.

**Technical Complexity:** Medium.

**Engineering Concepts Demonstrated:** Time-boxed entitlement accounting, override-resolution precedence logic, scheduled threshold monitoring.

**Acceptance Criteria:**
- A ticket created for an organization with an active SLA-override contract uses the override policy's response/resolution targets, not the tenant default.
- Logging time against a ticket whose organization has an active contract correctly decrements the visible remaining-hours figure.
- A contract past its `end_at` is excluded from SLA-override lookup (falls back to tenant default) without manual intervention.

---

### Track L — Workforce Management

**Purpose:** Extend assignment beyond load-balancing to account for agent skills and availability, and give supervisors visibility into capacity.

**User Problem:** Tickets requiring specific expertise (language, certification, product specialty) are routed with no regard for whether the assignee actually has that skill; there's no way to see who's actually available right now.

**Functional Requirements:**
- Agent skill profiles: a tagged set of skills per agent (e.g., `billing`, `spanish`, `network-tier2`), managed by admins or self-declared and approved.
- Shift schedule: per-agent recurring or one-off shift blocks defining expected availability windows.
- Real-time availability status (`available`/`busy`/`away`/`offline`), settable by the agent, auto-set to `offline` outside scheduled shifts (best-effort, not enforced).
- New queue assignment mode: `skill_based` — extends the existing `assignment_mode` enum (Track C7) rather than replacing round-robin/load-balanced; matches ticket required-skill tags (a new optional ticket/request-type field) against available, skilled agents.
- Supervisor capacity view: current open-ticket count per agent vs. a configurable capacity ceiling, with over-capacity agents flagged.

**Backend Requirements:**
- `WorkforceService`: skill CRUD, shift CRUD, `set_availability`, and a `find_skilled_available_agent(required_skills, queue_id)` matcher consumed by the existing assignment-mode dispatch logic in Track C7's implementation (extension point, not a rewrite).

**Frontend Requirements:**
- Agent: skill self-declaration (pending admin approval), availability toggle in navbar (adjacent to existing notification bell), personal shift calendar.
- Admin: skill catalog management, shift scheduling UI (calendar), capacity dashboard.
- Queue config: add `skill_based` to the existing assignment-mode selector, with a required-skills multi-select.

**Database/Data Model Changes:**
- `agent_skills` (agent_id, skill, approved_by nullable, approved_at nullable)
- `skills_catalog` (tenant_id, skill_code, label) — controlled vocabulary
- `agent_shifts` (id, agent_id, start_at, end_at, recurrence_rule nullable)
- `agent_availability` (agent_id, status, updated_at) — current state, single row per agent
- `ticket_required_skills` (ticket_id, skill) — optional tagging, settable manually or by request-type default (Track I)
- `queues.assignment_mode` enum extended with `skill_based` (alter existing column's check constraint)

**API Changes:**
- `POST /agents/{id}/skills`, `PATCH /agents/{id}/skills/{skill}/approve`
- `POST /agents/{id}/shifts`, `GET /agents/{id}/shifts`
- `PATCH /agents/me/availability`
- `GET /workforce/capacity` (supervisor dashboard data)

**Background Jobs / Events:** Scheduled job transitions availability to `offline` outside shift windows (soft signal, agent can override). Emits `agent.availability_changed` (consumed by the assignment matcher for real-time routing decisions).

**Authorization / Permissions:** `workforce.manage` (skills/shifts admin), agents manage their own availability without extra permission (already authenticated as themselves).

**Audit Requirements:** Skill approvals, shift changes (for schedule-dispute resolution).

**Notifications:** None new beyond existing assignment notifications; skill-approval decision notifies the requesting agent.

**Testing Requirements:** Skill-matching correctness tests (required skills subset of agent skills); no-available-skilled-agent fallback behavior test (must degrade gracefully, e.g., fall back to load-balanced, not fail assignment); shift-boundary availability tests.

**Observability:** Metrics: assignment success rate by mode, average time-to-skilled-assignment vs. average time-to-any-assignment (validates the feature earns its complexity), capacity-dashboard over-threshold count.

**Dependencies:** Extends Track C7 (existing assignment modes) — must not duplicate its dispatch logic, only add a new mode to it. Feeds Track M (QA scores tied to agent).

**Technical Complexity:** Medium.

**Engineering Concepts Demonstrated:** Constraint-based matching, extension of existing enum-driven dispatch logic without duplication, scheduled state transitions.

**Acceptance Criteria:**
- A queue configured `skill_based` with required skill `billing` only assigns to agents with that approved skill and `available` status.
- If no skilled available agent exists, the ticket falls back to the queue's configured secondary mode (or stays unassigned with a supervisor alert) rather than erroring.
- An agent's availability auto-transitions to `offline` when their current time falls outside all active shift blocks, and back to their last manual status when a shift begins (documented, testable behavior — not silent).

---

### Track M — Quality Assurance

**Purpose:** Give supervisors a structured, rubric-based review mechanism for ticket handling quality, separate from customer-facing CSAT.

**User Problem:** There's no internal quality signal beyond customer CSAT (which measures customer sentiment, not policy/process adherence), and no coaching workflow tied to review outcomes.

**Functional Requirements:**
- Configurable `Scorecard` templates: a set of weighted criteria (e.g., "greeting," "accurate resolution," "internal note quality," "SLA adherence") each scored on a defined scale.
- Sampling rules: admin-configured (e.g., "10% random sample of CLOSED tickets," "100% of SEV1 incidents," "100% of tickets flagged by CSAT ≤ 2") that populate a review queue.
- Supervisor review workflow: pick up a queued item, score against the scorecard, leave coaching notes, mark reviewed.
- Agent-facing score history (their own scores over time, coaching notes) — not other agents' scores.
- Aggregate scorecards per agent/team over a period, feeding into (and extending, not duplicating) the existing role-dashboard work from Track D3.

**Backend Requirements:**
- `QAService`: scorecard template CRUD, `enqueue_for_review` (triggered by sampling-rule evaluation on relevant events), `submit_review(ticket_id, scores, notes)`, aggregate score computation.
- Sampling-rule evaluation consumes Track O events (`ticket.status_changed` to CLOSED, `csat.submitted` with low score, `incident.closed` with SEV1/2) rather than polling.

**Frontend Requirements:**
- Admin: scorecard template builder (criteria + weights + scale), sampling rule configuration.
- Supervisor: review queue, scoring form embedded alongside the ticket transcript (read-only ticket view + scoring panel).
- Agent: personal score history/trend view, coaching notes feed.

**Database/Data Model Changes:**
- `qa_scorecard_templates` (id, tenant_id, name, criteria_json — [{key, label, weight, scale_max}])
- `qa_sampling_rules` (id, tenant_id, trigger_event, condition_json, sample_rate, is_active)
- `qa_reviews` (id, tenant_id, ticket_id, scorecard_template_id, reviewer_id, agent_id, scores_json, weighted_total, coaching_notes, reviewed_at)

**API Changes:**
- `POST /qa/scorecard-templates`, `POST /qa/sampling-rules`
- `GET /qa/review-queue`, `POST /qa/reviews` `{ticket_id, scorecard_template_id, scores, notes}`
- `GET /qa/agents/{id}/scores` (self or supervisor-viewed)

**Background Jobs / Events:** Consumes `ticket.status_changed`, `csat.submitted`, `incident.closed` events to evaluate sampling rules and enqueue reviews. Emits `qa.review_completed`.

**Authorization / Permissions:** `qa.manage` (templates/rules), `qa.review` (perform reviews, typically supervisor+), agents implicitly read their own scores.

**Audit Requirements:** Scorecard template changes (rubric changes affect fairness/history comparability — must be versioned, not silently mutated: template edits create a new version, old reviews retain the version they were scored against).

**Notifications:** New coaching note notifies the reviewed agent.

**Testing Requirements:** Sampling-rate statistical tests (over N events, enqueue rate approximates configured percentage within tolerance); weighted-score computation tests; template-versioning-preserves-historical-review tests.

**Observability:** Metrics: reviews completed/period, average score trend by agent/team, sampling-queue backlog size.

**Dependencies:** Track O (event consumption for sampling triggers), Track L (agent scorecard aggregation ties into workforce profiles).

**Technical Complexity:** Medium.

**Engineering Concepts Demonstrated:** Configurable rubric/schema modeling, statistical sampling, event-driven queue population, versioned-template historical integrity.

**Acceptance Criteria:**
- A sampling rule configured at 10% enqueues approximately 1 in 10 qualifying tickets over a large sample (statistical test with tolerance).
- Editing a scorecard template's weights does not alter the `weighted_total` of previously submitted reviews (verified by re-fetching a pre-edit review after the edit).
- An agent's `GET /qa/agents/{id}/scores` call for another agent's ID is rejected unless the caller has `qa.manage`/supervisor scope.

---

### Track P — Security Operations

**Purpose:** Provide differentiated handling for security-sensitive incidents and content, including PII surfacing and evidence integrity.

**User Problem:** Security-relevant tickets/incidents flow through the same undifferentiated pipeline as routine work, with no mandatory escalation, no sensitive-data safeguard, and no tamper-evident evidence handling.

**Functional Requirements:**
- `SecurityIncident` classification flag on Incidents (Track E) that, when set, mandatorily routes through a Track N workflow requiring security-team approval before any customer-visible communication is published (overrides the normal commander-discretion publishing flow).
- PII-detection scan (pattern-based: email, phone, SSN-shaped, credit-card-shaped patterns — **[Assumed]** scope; true NER-based detection is a future enhancement, not v1) run asynchronously on new ticket/comment content, flagging matches for reviewer attention (does not auto-redact in v1 — flags for human redaction decision, to avoid destroying legitimate content on false positives).
- Evidence attachments: an attachment mode for security incidents that computes and chains a SHA-256 hash with the previous evidence item's hash (simple hash-chain, not a full Merkle tree) to make post-hoc tampering detectable, and disables deletion for evidence-flagged attachments (retention override).
- Privileged-action approval: certain actions (e.g., closing a security incident, deleting an evidence attachment) require a second authorized approver (four-eyes principle), implemented as a Track N approval-gated workflow rather than a new bespoke mechanism.

**Backend Requirements:**
- `SecurityOpsService`: `flag_as_security_incident`, `scan_content_for_pii(text) -> matches[]` (regex-based scanner, tenant-configurable pattern list), `attach_evidence` (computes hash chain).
- PII scan runs as an async consumer of `ticket.created`/`comment.added` events (Track O), not inline in the request path, to avoid latency impact on ticket submission.

**Frontend Requirements:**
- Incident detail page: "Mark as Security Incident" action (permission-gated), which visibly changes the publish-approval requirement in the UI.
- PII-flag indicator on ticket/comment content with matched spans highlighted (reviewer decides redact/dismiss — dismissal recorded, not silent).
- Evidence attachment upload mode (separate from standard attachments) with hash-chain verification status displayed.

**Database/Data Model Changes:**
- `incidents.is_security_incident` (boolean, existing `incidents` table from Track E, altered)
- `pii_flags` (id, entity_type, entity_id, pattern_type, matched_span_redacted_preview, status[flagged/redacted/dismissed], reviewed_by, reviewed_at)
- `evidence_attachments` (id, incident_id, attachment_id — FK to existing attachments table, sha256_hash, previous_hash nullable, uploaded_by, uploaded_at) — deletion blocked at the service layer for rows in this table

**API Changes:**
- `POST /incidents/{id}/mark-security`
- `GET /pii-flags?status=`, `POST /pii-flags/{id}/resolve` `{action: redact|dismiss}`
- `POST /incidents/{id}/evidence` (multipart, wraps existing attachment upload + hash-chain computation)
- `GET /incidents/{id}/evidence/verify` (recomputes chain, returns integrity status)

**Background Jobs / Events:** Async PII scan job consuming `ticket.created`/`comment.added`. Emits `pii.flagged`, `security_incident.marked`.

**Authorization / Permissions:** `security.manage` (mark security incidents, resolve PII flags), evidence deletion blocked outright at the service layer regardless of permission (retention override, only reversible via a separate, heavily audited "evidence hold release" admin action — **[Assumed]** minimal v1 scope: no release mechanism at all, evidence is immutable for the record's lifetime).

**Audit Requirements:** Security-incident marking, every PII-flag resolution (redact/dismiss with reviewer identity), every evidence upload — these audit entries are themselves high-sensitivity and should be included in any legal-hold export (Track D6 dependency, not re-specified here).

**Notifications:** Security-incident marking notifies the security team role/queue; PII flags notify the ticket's assigned agent and a security reviewer.

**Testing Requirements:** Hash-chain integrity tests (tampering with a stored attachment's bytes is detected on verify); PII pattern-match tests (true/false positive fixtures); evidence-deletion-is-blocked test (attempt via direct service call, not just API, to ensure no bypass path); four-eyes approval tests (single approver cannot both request and approve).

**Observability:** Metrics: PII flags raised/resolved by action, security incidents by status, evidence chain verification failures (should be zero — alert if nonzero).

**Dependencies:** Track E (Incident Management), Track N (Workflow Orchestration) for four-eyes approval gates, Track O (event-driven PII scanning).

**Technical Complexity:** Medium-High.

**Engineering Concepts Demonstrated:** Async content scanning pipeline, hash-chain integrity verification, four-eyes authorization pattern, immutability enforcement at the service layer (not just UI).

**Acceptance Criteria:**
- Marking an incident as a security incident blocks any customer-visible timeline publish until a second, distinct user approves via the Track N workflow.
- A byte-level modification to a stored evidence attachment is detected by `GET /incidents/{id}/evidence/verify` (chain breaks at that item).
- Attempting to delete an evidence-flagged attachment via any code path returns a rejection, verified by a test that calls the service method directly (not just the route).
- A ticket comment containing a credit-card-shaped number produces exactly one `pii_flags` row referencing that comment, without exposing the full matched value in the flag list (preview only, e.g., last 4 digits).

---

### Track Q — DevOps / Monitoring-Triggered Incidents

**Purpose:** Let external monitoring/alerting systems open and correlate incidents automatically, closing the loop between the platform and the infrastructure it supports.

**User Problem:** Real incidents are usually detected by monitoring tools first; today, a human must notice the alert and manually create an incident, adding delay and losing the alert's structured context (which host, which metric, threshold breached).

**Functional Requirements:**
- Inbound alert-ingestion endpoint accepting a generic payload shape plus adapters normalizing common formats (**[Assumed]** initial adapter scope: a generic webhook JSON shape and one named example, e.g., a Prometheus Alertmanager-style payload — exact third-party format support should be confirmed against actual target tools before implementation).
- Deduplication: repeat alerts for the same underlying condition (matched by an adapter-provided fingerprint, e.g., alertname+labels) within a window update the existing open incident's timeline rather than creating a new incident.
- Auto-creates an `Incident` (Track E) on a new-fingerprint alert, pre-populated with severity mapped from the alert's priority field, and links the affected asset/service if the alert payload identifies one matching an existing Asset (Track H) by a configured external-ID field.
- Change correlation: if a Change (Track G) affecting the same service completed within a configurable recent window, surface it on the newly created incident automatically (uses the same correlation logic Track G already implements from the other direction).
- Resolution: an inbound "alert resolved" payload for a known fingerprint auto-adds a timeline entry (does not auto-close the incident — human confirmation required to close, since alert-resolved doesn't always mean genuinely fixed).

**Backend Requirements:**
- `AlertIngestionService`: `POST /integrations/alerts/{adapter_name}` per-adapter parsing → normalized internal alert shape → `find_or_create_incident(fingerprint, ...)`.
- Adapter pattern: a base normalizer interface with per-source implementations, so adding a new monitoring tool's format doesn't touch core ingestion logic.
- Fingerprint-based dedup lookup against recent open incidents (indexed on a `source_fingerprint` column).

**Frontend Requirements:**
- Admin: alert-source configuration (register an inbound webhook URL/secret per adapter, view recent ingestion log for debugging misconfigured sources).
- Incident detail page: "Source: Alert (Datadog)" badge and raw-alert-payload viewer (collapsed by default) when incident originated from an alert, distinct from manually created incidents.

**Database/Data Model Changes:**
- `alert_sources` (id, tenant_id, adapter_name, webhook_secret_hash, is_active)
- `ingested_alerts` (id, alert_source_id, source_fingerprint, raw_payload_json, normalized_severity, incident_id nullable, received_at, status[created_incident/updated_incident/resolved_entry])
- `incidents.source` (existing enum from Track E extended with `alert` value), `incidents.source_alert_id` nullable FK

**API Changes:**
- `POST /integrations/alerts/{adapter_name}` (authenticated via per-source webhook secret, not user JWT)
- `GET /alert-sources`, `POST /alert-sources`
- `GET /alert-sources/{id}/ingestion-log`

**Background Jobs / Events:** Emits `alert.received`, `incident.opened` (source=alert) — reuses Track E's existing event, tagged with source. Consumes nothing (this is an ingestion boundary).

**Authorization / Permissions:** Inbound endpoint uses a per-source shared secret (not user auth) — validated via HMAC signature over the payload, analogous to standard webhook security practice; `alert_source.manage` for admin configuration.

**Audit Requirements:** Alert-source configuration changes (secret rotation, activation/deactivation) audited; individual alert ingestions are logged in `ingested_alerts` rather than the general audit log (high volume, different retention needs).

**Notifications:** New alert-created incident follows Track E's normal severity-based notification path (e.g., SEV1 pages supervisors) — no separate notification path needed.

**Testing Requirements:** Fingerprint-dedup tests (repeat alert updates, doesn't duplicate); adapter-parsing tests per supported format; invalid-signature rejection tests; change-correlation-on-alert-creation tests.

**Observability:** Metrics: alerts ingested/min by source, dedup rate, alert-to-incident latency, invalid-signature rejection count (security signal).

**Dependencies:** Track E (Incident Management), Track G (Change correlation reuses its logic), Track H (asset linking, optional).

**Technical Complexity:** Medium.

**Engineering Concepts Demonstrated:** Adapter pattern for heterogeneous integrations, idempotent/deduplicated ingestion, HMAC webhook authentication, external-system correlation.

**Acceptance Criteria:**
- Two alert payloads with the same fingerprint received 5 minutes apart update one incident's timeline rather than creating two incidents.
- An alert payload with an invalid HMAC signature is rejected with 401 and does not create any incident or ingestion record beyond a rejected-attempt log entry.
- An alert mapping to a service with a Change completed in the last hour automatically surfaces that change on the created incident without human action.

---

### Track R — Advanced AI Operations

**Purpose:** Apply AI to cross-entity operational intelligence — prediction and correlation — building on the domain objects this plan introduces, explicitly beyond Track C12's single-ticket content generation.

**User Problem:** Agents/supervisors have no forward-looking signal (which tickets are at breach risk before they breach) and no assisted way to draft the post-incident review that Track E requires — both currently fully manual.

**Functional Requirements, classified by autonomy tier per the required convention:**

1. **Predictive SLA-breach risk scoring** — *Assistive.* A background scorer (feature-based: current elapsed time vs. target, agent's current load, ticket category historical breach rate) computes a 0–100 risk score per active ticket, surfaced as a sortable column/filter on the ticket list and a dashboard widget ("N tickets at high breach risk"). No automatic action taken — purely informational, ranks work for agents/supervisors.
2. **Similar-incident detection** — *Human-in-the-loop.* Extends Track E's deterministic (affected-service) duplicate check with embedding-similarity search over incident titles/descriptions (using a vector column and nearest-neighbor query — **[Assumed]** requires a vector-capable index, e.g., pgvector) to surface likely-related past incidents even without service overlap. Presented as suggestions on incident creation; commander decides whether to link.
3. **Automatic post-incident-review drafting** — *Semi-automated.* On incident closure, generate a draft PIR (impact summary, timeline condensed to key events, suggested root-cause candidates drawn from the timeline text) from the structured timeline data (Track E) using the existing AI-assistance infrastructure (Track C12's model integration, reused not duplicated). The draft is never auto-published — a human must review and submit the PIR (per Track E's acceptance criteria, PIR completion is a human action).

**Explicitly not included in v1** (noted for the Section 16 rejection list too, but worth flagging here): fully automated incident classification/severity assignment, and fully automated remediation actions — both require a much higher confidence/trust bar than this plan's engineering scope justifies at this stage.

**Backend Requirements:**
- `RiskScoringService`: scheduled (or event-triggered on relevant state changes) computation writing to a `ticket_risk_scores` table (not computed on every read — avoids expensive per-request scoring).
- `SimilarityService`: embedding generation on incident create/update (calls existing AI infrastructure from C12), stored in a vector column, queried via nearest-neighbor on new-incident creation.
- `PIRDraftService`: on `incident.closed` event (Track O), assembles timeline text and calls the existing AI-assistance completion endpoint (C12) with a structured prompt, stores the draft for the PIR form to pre-populate.

**Frontend Requirements:**
- Ticket list: risk-score column/badge, sortable, with a "high risk" quick filter.
- Incident creation form: "similar incidents" suggestion panel (title + similarity indicator, link action).
- PIR form (Track E): pre-populated fields from the draft, clearly labeled "AI-drafted — review before submitting," fully editable.

**Database/Data Model Changes:**
- `ticket_risk_scores` (ticket_id, score, computed_at, contributing_factors_json)
- `incidents.embedding` (vector column, nullable, populated async)
- `pir_drafts` (incident_id, draft_json, generated_at, model_version)

**API Changes:**
- `GET /tickets/{id}/risk-score` (or included inline in ticket list response)
- `GET /incidents/similar?title=&description=` (used by creation-time suggestion)
- `GET /incidents/{id}/pir-draft`

**Background Jobs / Events:** Risk scoring triggered on a schedule and on `ticket.status_changed`/`sla.first_responded` events (Track O). Embedding generation triggered on `incident.opened`/`incident.updated`. PIR draft generation triggered on `incident.closed`.

**Authorization / Permissions:** Reuses `ticket.view`/`incident.view` — AI-derived data inherits the same visibility as its source entity, no new permission needed.

**Audit Requirements:** PIR draft generation logged (model version used, for reproducibility/dispute purposes) — not the draft content itself in the audit log (lives in `pir_drafts`), just the generation event.

**Notifications:** High-risk-score tickets crossing a configurable threshold can optionally notify the assignee (reuses existing notification infrastructure) — off by default to avoid alert fatigue, admin-configurable.

**Testing Requirements:** Risk-score computation unit tests (known-input fixtures produce expected score ranges); similarity search relevance tests against a fixture set; PIR-draft-never-auto-submits test (asserts the incident's PIR remains incomplete until explicit human submission per Track E's own acceptance criteria); model-failure graceful-degradation tests (AI service unavailable → feature degrades to "no suggestion," never blocks the underlying workflow).

**Observability:** Metrics: risk-score distribution, similarity-suggestion click-through rate (are they useful?), PIR-draft edit distance from final submitted PIR (measures draft quality over time), AI-service error rate and fallback rate.

**Dependencies:** Track E (Incident Management) as the primary data source, Track O (event triggers), existing C12 AI infrastructure (reused, not duplicated), pgvector or equivalent extension for similarity search — **[Assumed]** infrastructure availability, must be confirmed/provisioned.

**Technical Complexity:** High.

**Engineering Concepts Demonstrated:** Feature-based predictive scoring, vector similarity search, AI-infrastructure reuse across features, human-in-the-loop design discipline (explicit autonomy-tier classification enforced in both product and test design), graceful degradation on external-service failure.

**Acceptance Criteria:**
- Risk scores are recomputed on a defined cadence and reflect input changes within one cycle (e.g., an agent's load increasing measurably shifts scores for their open tickets on the next run).
- Similarity search returns incidents ranked by embedding distance and excludes the incident being created from its own suggestions.
- A PIR draft exists after incident closure but the incident's `post_incident_reviews.completed_by` remains null until a human explicitly submits — verified by a test that closes an incident and asserts PIR completion state is unaffected by draft generation.
- If the AI completion service returns an error, PIR draft generation fails silently to "no draft available" without blocking the incident-closure transition itself.

---

## 6. Cross-Cutting Architecture Changes

### 6.1 Transactional Outbox (underlies Track O)
- **Architecture:** Every state-changing service method writes its domain event row in the same DB transaction as the state mutation; a separate relay process/loop reads and publishes.
- **Rationale:** Guarantees no event is lost due to a crash between "state saved" and "event published," and no event is falsely published if the transaction rolls back — the two failure modes that plague naive "publish after commit" designs.
- **Components:** `outbox_events` table, `EventRelay` (extends existing worker loop), `event_deliveries` tracking table.
- **Data flow:** Service method → single DB transaction (business tables + outbox insert) → commit → relay polls → consumer dispatch → delivery status update.
- **Dependencies:** Existing worker process and `SKIP LOCKED` job-claiming pattern (extended, not replaced).
- **Migration considerations:** Additive tables only; no changes to existing tables required to introduce the outbox itself (individual features alter their own tables to call `emit_event()`).
- **Failure modes:** Relay crash mid-batch (mitigated by `SKIP LOCKED` + delivery-status idempotency); consumer perpetually failing (mitigated by dead-letter after N attempts); outbox table unbounded growth (mitigated by a retention/archival job on `published_at`, analogous to existing audit-log retention from B8).
- **Testing strategy:** Transaction-rollback-produces-no-event tests; crash-simulation tests (kill relay mid-poll, assert no duplicate/lost delivery on restart); dead-letter threshold tests.

### 6.2 Workflow Orchestration Runtime (underlies Track N)
- **Architecture:** Interpreter-style engine reading declarative `workflow_definitions` graphs, advancing `workflow_runs` in response to consumed domain events, persisting all state transitions for durability/resumability.
- **Rationale:** A single, well-tested engine avoids five different domains (Change, Request Fulfillment, Task, Problem, Security four-eyes) each implementing bespoke, subtly-different approval/sequencing logic.
- **Components:** `WorkflowEngineService`, definition graph interpreter, timer integration (existing job queue), approval-gate handler.
- **Data flow:** Domain event (Track O) → engine checks for waiting runs matching the event → advances matched step → may emit further events (e.g., `workflow.step_completed`) → may enqueue a timer job → may notify an approver.
- **Dependencies:** Track O (event-driven advancement).
- **Migration considerations:** Entirely additive; existing Track C10 approval gate can remain as-is for simple ticket-close approvals, or be migrated to a trivial one-step workflow definition later — not required for this plan's scope.
- **Failure modes:** Malformed definition graph (validated at publish time, not at run time, to fail fast); run stuck in `waiting` indefinitely (mitigated by optional step-level timeout → auto-escalation, configurable per step); compensation action itself failing (logged, surfaced to admin, not silently swallowed).
- **Testing strategy:** Per-step-type unit tests, full-graph integration tests for each domain's actual definition (Change approval, Request fulfillment, Security four-eyes), chaos test (kill process mid-run, assert correct resumption).

### 6.3 Domain Event Schema Registry
- **Architecture:** Every event type has a versioned JSON schema (**[Assumed]** lightweight — a schema-version integer per event type plus documented payload shape, not necessarily a formal schema-registry service) so consumers can handle multiple payload versions during rollout.
- **Rationale:** As Tracks E–R are built incrementally, event payloads will evolve; without versioning, a consumer deployed before a payload change breaks silently.
- **Components:** `schema_version` column on `outbox_events` (already specified in 6.1/Track O); a lightweight in-code registry mapping `(event_type, schema_version) → payload validator`.
- **Data flow:** Producer tags the event with its current schema version at emit time; consumer checks the version and applies the appropriate parsing path (or rejects/dead-letters unknown versions).
- **Dependencies:** Track O.
- **Migration considerations:** New event types start at version 1; breaking payload changes increment the version rather than mutating in place.
- **Failure modes:** Consumer encountering an unrecognized version dead-letters rather than guessing — explicit failure over silent corruption.
- **Testing strategy:** Multi-version payload fixture tests per event type; unknown-version dead-letter test.

### 6.4 Polymorphic Parent Reference Pattern (underlies Task Management, and reused by others)
- **Architecture:** `parent_type` (enum) + `parent_id` (uuid/int) pair instead of five separate `task_ticket_id`/`task_change_id`/... nullable foreign keys.
- **Rationale:** Task Management (and evidence attachments, and a few other places) attach to multiple entity types; a proper FK per type doesn't scale as new parent types are added and forces schema migrations for each new consumer.
- **Components:** Standard `(parent_type, parent_id)` columns, enforced application-side (not DB-level FK, since Postgres can't polymorphically FK) with an application-layer existence check on write.
- **Data flow:** Write path validates `parent_id` exists for the given `parent_type` before insert; read path always filters by both columns together (never `parent_id` alone) to avoid cross-type collisions.
- **Dependencies:** None.
- **Migration considerations:** Requires disciplined indexing — always a composite index on `(parent_type, parent_id)`, never `parent_id` alone.
- **Failure modes:** Orphaned rows if a parent is hard-deleted without cascading (mitigated by preferring soft-delete/status fields over hard deletes for parent entities, consistent with the existing platform's apparent pattern of status enums over deletion).
- **Testing strategy:** Cross-type isolation tests (task for parent A never appears in parent B's query), orphan-prevention tests (write rejected if parent doesn't exist).

---

## 7. Database Evolution

**New tables** (grouped by track, full column detail in Section 5):
`workflow_definitions`, `workflow_runs`, `workflow_run_steps`, `workflow_run_events` (N) · `outbox_events`, `event_deliveries` (O) · `incidents`, `incident_services`, `incident_tickets`, `incident_timeline_entries`, `post_incident_reviews` (E) · `problems`, `problem_incidents`, `problem_tickets`, `problem_actions` (F) · `change_requests`, `change_services`, `change_plan_steps`, `blackout_periods`, `change_incident_links` (G) · `assets`, `asset_attributes`, `asset_type_attribute_schemas`, `asset_relationships`, `asset_services`, `ticket_assets` (H) · `services`, `request_types`, `service_requests` (I) · `tasks`, `task_dependencies`, `task_checklist_items`, `task_templates`, `task_template_items` (J) · `contracts`, `time_entries` (K) · `agent_skills`, `skills_catalog`, `agent_shifts`, `agent_availability`, `ticket_required_skills` (L) · `qa_scorecard_templates`, `qa_sampling_rules`, `qa_reviews` (M) · `pii_flags`, `evidence_attachments` (P) · `alert_sources`, `ingested_alerts` (Q) · `ticket_risk_scores`, `pir_drafts` (R)

**Altered tables:**
- `incidents.is_security_incident` (P), `incidents.source_alert_id` (Q), `incidents.embedding` vector column (R)
- `queues.assignment_mode` check constraint extended with `skill_based` (L)
- `tickets` gains no new columns directly — cross-references are via join tables (`ticket_assets`, `ticket_required_skills`) to avoid widening the core ticket table for every new domain, deliberately

**Key indexes:**
- `outbox_events(published_at)` (relay polling), `outbox_events(entity_type, entity_id)` (replay)
- `incidents(status, severity)`, `incident_services(service_id)` (correlation queries)
- `change_requests(scheduled_start, scheduled_end)` + `blackout_periods(start_at, end_at)` (conflict detection — range-overlap queries, consider a GiST index on a `tstzrange` if query volume justifies it)
- `asset_relationships(source_asset_id)` and `(target_asset_id)` both directions (traversal)
- `tasks(parent_type, parent_id)` composite (per 6.4)
- `contracts(organization_id, status)` (SLA-override lookup hot path)
- `incidents.embedding` — vector index (ivfflat/hnsw depending on chosen extension) for similarity search (R)

**Constraints:**
- `asset_relationships`: application-enforced cycle prevention (not DB-expressible for arbitrary-depth cycles) plus a CHECK preventing `source_asset_id = target_asset_id`
- `task_dependencies`: application-enforced acyclic check on write (same rationale)
- `workflow_definitions`: unique `(tenant_id, name, version)`
- `contracts`: partial unique index ensuring at most one `active` contract per organization at a time (business rule — one active support contract, historical ones remain as `expired`/`cancelled` rows)

**Enums/state machines:** Each of Incident, Problem, ChangeRequest, ServiceRequest(via Ticket), Task, WorkflowRun introduces its own status enum, deliberately kept separate from the existing ticket-status enum rather than overloading it — these are different lifecycles with different meanings, and conflating them (e.g., trying to make "incident status" a flavor of "ticket status") would be the kind of superficial-extension anti-pattern this plan is explicitly instructed to avoid.

**JSONB usage — deliberate, not default:**
- `workflow_definitions.graph_json`, `workflow_run_steps.input_json/output_json`, `workflow_run_events.payload_json` — genuinely variable-shape, versioned data; normalized modeling would be impractical and JSONB is the right call.
- `qa_scorecard_templates.criteria_json` — tenant-configurable schema, read as a whole for rendering, not queried column-by-column.
- **Explicitly NOT JSONB:** asset attributes use EAV (`asset_attributes`) with a schema registry (`asset_type_attribute_schemas`) rather than a JSONB blob, because attribute values need to be individually queryable/filterable ("find all assets where `ram_gb > 16`") — a use case JSONB serves poorly compared to typed EAV rows, per the task's explicit instruction not to default to JSONB where relational modeling fits better.

---

## 8. API Evolution

- **Resource-oriented, versioned under the existing `/api/v1` prefix** — no new API version needed, these are additive resources.
- **New top-level resources:** `/incidents`, `/problems`, `/changes`, `/blackout-periods`, `/assets`, `/services`, `/service-requests`, `/tasks`, `/task-templates`, `/contracts`, `/workforce/*`, `/qa/*`, `/pii-flags`, `/alert-sources`, `/workflows/*`, `/events`.
- **Filters/pagination:** All list endpoints follow the existing `?page=&size=` convention and existing filter-param style (`?status=&priority=` pattern from tickets extended per-resource, e.g., `?status=&severity=` for incidents).
- **Commands vs. CRUD:** State transitions are modeled as explicit action endpoints (`POST /incidents/{id}/transitions`, `POST /changes/{id}/submit`) mirroring the existing ticket-transition pattern (`POST /tickets/{id}/transitions`), not overloaded PATCH — consistent with the platform's existing convention of a dedicated transitions endpoint plus a legacy PATCH where needed.
- **Idempotency:** `Idempotency-Key` header support extends to all new POST-that-creates-state-changing-effects endpoints, especially `POST /service-requests` (creates 3 rows atomically) and `POST /integrations/alerts/{adapter}` (external systems will retry on timeout) — reusing the existing idempotency-record mechanism, not a new one.
- **Authorization:** Every new endpoint maps to a new or existing permission per the tables in Section 5; the inbound alert-ingestion endpoint is the one deliberate exception, authenticated via per-source HMAC secret instead of user JWT, documented explicitly as a different trust boundary.
- **Event behavior:** Every state-changing endpoint that matters for correlation/workflow purposes emits an `outbox_events` row in the same transaction (Section 6.1) — this is a cross-cutting API contract, not per-endpoint discretion.

---

## 9. Event / Workflow Architecture

| Event | Producer | Payload Concept | Consumers | Retry Behavior | Idempotency | Failure Handling |
|---|---|---|---|---|---|---|
| `incident.opened` | Incident Service | incident_id, severity, affected_services[] | Problem (recurrence scan), Workforce (notify on-call), Track R (embedding gen) | At-least-once, 5 attempts, exponential backoff | Consumer dedups by event_id | Dead-letter after 5 attempts, admin-visible |
| `incident.closed` | Incident Service | incident_id, pir_completed | Problem (auto-create if root cause set), QA (sampling trigger), Track R (PIR draft — note: draft fires on closure trigger, PIR itself is post-closure human step) | Same as above | Same | Same |
| `change.approved` | Workflow Engine (via `workflow.run_completed`) | change_id, approver_id | Change Service (advance to SCHEDULED) | Same | Same | Same |
| `task.completed` | Task Service | task_id, parent_type, parent_id | Workflow Engine (advance waiting steps), Change/Request Fulfillment progress display | Same | Same | Same |
| `alert.received` | Alert Ingestion | source_fingerprint, normalized_severity | Incident Service (find_or_create) | Synchronous within ingestion request (not outbox-deferred, since the caller expects a definitive response) — internally still emits `incident.opened` via outbox for downstream consumers | Fingerprint-based dedup, not just event_id | Ingestion failure returns 5xx to caller (external system's own retry handles it) |
| `ticket.status_changed` (existing, Track A/B) | Ticket Service | ticket_id, from_status, to_status | QA (sampling trigger), Track R (risk-score recompute trigger) | Existing behavior extended with new consumers | Existing | Existing |
| `workflow.step_completed` | Workflow Engine | run_id, step_id | Notification system (approval-pending alerts) | Same as row 1 | Same | Same |

**General retry/idempotency/failure policy** (applies to all rows unless noted): consumers are required to be idempotent on `event_id`; the relay retries failed consumer calls with exponential backoff up to a configurable max attempt count (default 5), after which the delivery is marked `dead_letter` and surfaced in the admin Event Log (Track O) for manual investigation/replay.

---

## 10. Security & Governance

- **New trust boundary:** The alert-ingestion endpoint (Track Q) is the first unauthenticated-by-user-JWT inbound surface beyond the existing public KB/status pages — it must be treated with the same scrutiny as the existing public API key model (HMAC signature validation, replay-attack window, secret rotation support).
- **Immutable evidence (Track P):** Evidence attachments are the first genuinely append-only/undeletable data in the platform; this needs explicit documentation for admins (they cannot be deleted even by OWNER role through normal channels) and a corresponding note in any data-retention/GDPR tooling (Track D6) that evidence attachments are excluded from standard right-to-be-forgotten redaction unless a separate legal process applies (**[Assumed]** — the interaction between evidence immutability and GDPR erasure requests is a genuine legal question this plan flags but does not resolve; recommend legal review before implementation).
- **Four-eyes enforcement (Track P):** The Track N workflow engine must guarantee an approval step's approver cannot be the same user as the step's initiator — this is a server-side invariant, not just a UI restriction, and should be tested accordingly (already reflected in Track P's acceptance criteria).
- **Segregation of duties (general):** As new `*.manage` permissions are introduced (workflow, incident, change, contract, workforce, qa, security), the permission catalog should be reviewed for over-broad grants — e.g., `change.approve` (CAB) should not be automatically implied by `change.create`, since self-approval of one's own change request defeats the purpose of change control.
- **PII handling (Track P):** The pattern-based PII scanner is explicitly a detection aid, not a compliance guarantee — its false-negative rate should be documented and communicated to stakeholders so it isn't relied upon as a sole compliance control.
- **Audit completeness:** Every new track's Audit Requirements (Section 5) feed the existing audit log infrastructure (`audit_logs`, Track B8 retention) — no new audit subsystem is introduced, preserving a single source of truth for compliance review.

---

## 11. Testing Strategy

- **Unit tests:** Per-service business logic (state machine transitions, risk scoring, hash-chain computation, dependency-cycle detection) — required for every service listed in Section 5.
- **Integration tests:** Cross-entity flows that span tables/services — e.g., "submit service request → ticket + service_request + workflow_run created atomically," "close incident with root cause → problem auto-created," "alert received → incident created → change correlation surfaced."
- **API tests:** Contract tests per new endpoint (request/response shape, permission enforcement, pagination) extending the existing `test_api.py` pattern.
- **Permission tests:** A matrix test per new permission verifying both the positive case (authorized user succeeds) and negative case (unauthorized user gets 403) — extends the existing permission-matrix testing called for in Track B9.
- **State-machine tests:** Every new lifecycle (Incident, Problem, Change, ServiceRequest via ticket, Task, WorkflowRun) needs an exhaustive valid/invalid-transition test table, mirroring the existing ticket-lifecycle test approach.
- **Workflow tests:** Full-graph execution tests for each domain's actual production workflow definition (Change CAB approval, Request Fulfillment provisioning, Security four-eyes) — not just engine-level unit tests, but "does the real definition behave correctly end-to-end."
- **Concurrency tests:** Two approvers racing on one approval step (exactly one should win/be recorded); two alerts with the same fingerprint arriving simultaneously (exactly one incident should be created, not two); task-dependency completion races.
- **Failure/retry tests:** Outbox relay crash-and-resume; workflow engine crash mid-run resume; dead-letter threshold behavior; AI-service-unavailable graceful degradation (Track R).
- **Performance tests:** Asset dependency traversal at realistic depth/fanout; risk-score computation at realistic ticket volume; embedding similarity search latency at realistic incident-history volume — these should feed into the existing load-testing harness (Track D11) rather than a separate tool.
- **End-to-end tests:** At minimum one full scenario per major track — e.g., "monitoring alert fires → incident auto-created → commander assigned → tickets linked → customer-visible update published → PIR completed → problem created → corrective task tracked to completion" exercises Tracks E, F, J, O, Q, R together and is the single highest-value E2E test this plan can specify.

---

## 12. Observability

- **Metrics** (Prometheus-style, extending Track B10's baseline): per-track metrics are specified in each feature's Observability subsection (Section 5); cross-cutting ones worth calling out again: outbox relay lag, workflow run failure rate, dead-letter queue depth, MTTD/MTTA/MTTR for incidents, change success rate, evidence chain verification failures (should always be zero).
- **Logs:** All new services log with the existing `request_id` correlation pattern (Track B10); workflow runs additionally log with `run_id` for cross-step correlation; alert ingestion logs with `source_fingerprint` for dedup debugging.
- **Traces:** Workflow step execution and outbox relay dispatch are the two highest-value new trace spans — both involve asynchronous, multi-hop execution that's otherwise hard to debug from logs alone.
- **Alerts (operational, i.e., alerting on the platform itself, distinct from Track Q's inbound alerts):** Relay lag exceeding threshold; dead-letter queue depth exceeding threshold; SEV1 incident open beyond target duration; evidence chain verification failure (should page immediately — indicates tampering or corruption); AI service (Track R) error rate spike.
- **Operational dashboards:** An "Incident Command Center" view (open incidents by severity, MTTR trend, on-call status from Workforce) and a "Change Calendar & Risk" view (upcoming changes, blackout conflicts, recent change success rate) are the two highest-value new operational dashboards, both composing data already specified per-track rather than requiring new aggregation infrastructure beyond what's listed.

---

## 13. Prioritization

| Priority | Feature | Value | Complexity | Dependencies | Recommendation |
|---|---|---|---|---|---|
| P0 | Track O — Event-Driven Architecture | Very High | High | None | Build first; everything else assumes it |
| P0 | Track N — Workflow Orchestration Engine | Very High | High | Track O | Build second; Tracks G/I/J/P consume it |
| P0 | Track E — Incident Management | Very High | High | Track O | Core differentiator; build early |
| P1 | Track J — Work/Task Management | High | Medium | None | Cheap, unlocks G/I/F |
| P1 | Track G — Change Management | High | High | N, J, E | High enterprise value |
| P1 | Track H — Asset/CMDB | High | Medium | None (standalone) | Independent track, parallelizable |
| P1 | Track Q — DevOps/Monitoring Integration | High | Medium | E, O | Strong engineering differentiator, moderate cost |
| P2 | Track I — Service Catalog & Request Fulfillment | High | Medium-High | N, existing C9 | High volume-reduction value, do after N/J stable |
| P2 | Track F — Problem Management | Medium-High | Medium | E, J | Natural follow-on to E |
| P2 | Track K — Contract & Entitlement | Medium | Medium | None (standalone) | Commercial value depends on business model |
| P2 | Track L — Workforce Management | Medium | Medium | Extends existing C7 | Value scales with team size |
| P3 | Track M — Quality Assurance | Medium | Medium | O, L | Valuable but not urgent |
| P3 | Track P — Security Operations | Medium-High (situational) | Medium-High | E, N, O | High value if security-sensitive; else defer |
| P4 | Track R — Advanced AI Operations | Medium | High | E, O, C12, vector infra | Experimental infra dependency (pgvector); highest risk/uncertainty |

---

## 14. Recommended Implementation Phases

**Phase A — Foundations (must come first, nothing else is buildable without these)**
Track O (Event-Driven Architecture) → Track N (Workflow Orchestration Engine).
*Rationale:* Every subsequent track either consumes domain events or workflow runs (or both). Building any domain track first would force either a throwaway bespoke implementation later replaced by N/O, or silent duplication of exactly the logic this plan is designed to avoid duplicating.

**Phase B — Core Incident Capability**
Track E (Incident Management) → Track J (Task Management, can run in parallel with E — no dependency between them).
*Rationale:* Incident Management is the single highest product-value addition and depends only on O. Task Management is cheap, independent, and is a dependency for three later tracks (F, G, I) — sequencing it early avoids blocking them later.

**Phase C — Operational Depth**
Track Q (Monitoring Integration) → Track F (Problem Management) → Track H (Asset/CMDB, parallelizable — no dependency on Q/F).
*Rationale:* Q and F both directly extend E and deliver visible value quickly once E exists. H has no dependencies and can be staffed in parallel by a separate contributor.

**Phase D — Governed Change & Service Delivery**
Track G (Change Management) → Track I (Service Catalog & Request Fulfillment).
*Rationale:* Both consume N (workflow engine, proven by now in E/Q) and J (tasks). G additionally benefits from H (asset/service linkage) and Q (change-correlation) already existing. I additionally reuses the existing C9 custom-fields primitive, which should be stable by this phase.

**Phase E — Commercial & People Operations**
Track K (Contract & Entitlement) → Track L (Workforce Management) — independent of each other, parallelizable.
*Rationale:* Neither blocks nor is blocked by the incident/change/asset work; sequenced after the core ITSM loop is proven so they don't compete for the same engineering attention during the highest-risk foundational work (Phase A/B).

**Phase F — Quality, Security, Intelligence**
Track M (QA) → Track P (Security Operations) → Track R (Advanced AI Operations).
*Rationale:* M depends on O and benefits from L existing (agent scorecards). P depends on E and N being mature/trusted (four-eyes approval is only as good as the workflow engine executing it). R is placed last deliberately — it depends on E's timeline data being populated by real usage to be meaningfully testable/valuable, and carries the most infrastructure risk (vector search dependency), so it should not compete for priority against the core ITSM domains.

---

## 15. Top 10 Highest-Value Additions

Ranked by Product Value + Engineering Depth + Differentiation + Reasonable Complexity:

1. **Track E — Incident Management** — the single most recognizable "this is now a real ITSM platform" feature; strong but tractable engineering (independent state machine, timeline, dual-audience publishing).
2. **Track O — Event-Driven Architecture** — pure engineering depth (outbox pattern, at-least-once delivery, dead-lettering) that's invisible to end users but is the strongest distributed-systems portfolio artifact in this entire plan.
3. **Track N — Workflow Orchestration Engine** — the other deep engineering artifact; durable execution and compensation are genuinely hard problems, done once and reused four times.
4. **Track G — Change Management** — high enterprise/compliance value, meaningfully differentiated from the generic approval gate, moderate-high complexity that's well justified by the value.
5. **Track Q — DevOps/Monitoring-Triggered Incidents** — closes the loop with real infrastructure, adapter-pattern engineering is clean and demonstrable, moderate complexity.
6. **Track J — Work/Task Management** — cheap relative to its leverage; unlocks three other tracks; clean DAG-modeling engineering exercise.
7. **Track H — Asset/CMDB** — standalone, high real-world value (impact analysis), good relational-modeling showcase (EAV + schema registry done deliberately, not lazily).
8. **Track I — Service Catalog & Request Fulfillment** — highest ticket-volume real-world impact of any single feature (self-service request deflection), reuses infrastructure cleanly rather than duplicating it.
9. **Track F — Problem Management** — meaningful ITIL-recognized value at moderate cost, clean natural extension of Incident.
10. **Track P — Security Operations** — high value where applicable, and the hash-chain/four-eyes mechanics are a distinctive, non-generic engineering showcase not many portfolio ITSM projects attempt.

*(Tracks K, L, M, R are valuable but ranked below the top 10 due to narrower applicability (K, L depend heavily on business model/team size) or higher uncertainty/lower engineering novelty relative to their cost (M, R).)*

---

## 16. Deliberately Rejected Features

- **A visual drag-and-drop workflow builder UI (vs. structured-JSON-with-preview editor).** Attractive for demos, but it's a substantial standalone frontend engineering project orthogonal to the backend orchestration value this plan targets; a structured editor with live preview delivers 80% of the usability for a fraction of the cost. Revisit only if the platform pursues a low-code positioning.
- **Fully automated incident classification/severity assignment (Track R taken further).** Rejected for this plan's scope: getting automatic severity assignment wrong has real operational cost (under-severity delays response, over-severity causes alert fatigue), and the confidence bar for full automation here is higher than what a first AI-ops iteration should target. Kept as assistive/human-in-the-loop per Track R's explicit classification.
- **A second, ITSM-specific approval-workflow UI competing with Track N.** Considered building Change/Request approvals as their own bespoke mini-workflow system for simplicity; rejected specifically because it would duplicate Track N's engine, which is exactly the anti-pattern this plan's Phase 2 audit instructions call out.
- **Full double-entry billing/invoicing tied to Contract & Entitlement (Track K).** Time-entry and consumption tracking are in scope; generating actual invoices, handling payment processing, or dunning is out of scope — that's Track D10's territory if/when the multi-tenant commercial model (Track D4) is finalized, and building it here would be premature and duplicate future work.
- **A general-purpose CMDB visual graph/network diagram UI for Asset relationships.** The data model (Track H) supports full graph traversal; a rich visual network-diagram frontend is a substantial, separable UI investment. Shipping list-based "depends on / depended on by" panels first is the right sequencing — a graph visualization can be layered on later without any backend change.
- **NER/ML-based PII detection (vs. pattern-based, Track P).** Considered for better recall; rejected for v1 because it introduces a much larger scope (model selection, false-positive tuning, potential need for a dedicated NLP service) relative to the value increment over well-tuned regex patterns for the common structured-PII cases (SSN, credit card, email, phone). Documented as a explicit future enhancement, not silently downgraded.
- **Merging Incident status and Ticket status into one unified enum.** Considered for "simplicity"; rejected because they represent genuinely different things (service impact state vs. individual work-item state) — a ticket linked to an incident can be RESOLVED while the incident is still MONITORING, and conflating the enums would make that impossible to represent correctly.
- **A dedicated microservice/separate deployable per new domain (Incident service, Change service, etc. as independent processes).** Rejected as premature distributed-systems complexity for the current scale — Track O's outbox/event pattern gives the *internal* decoupling benefits (reliable async processing, clear domain boundaries in code) without the operational cost of running and coordinating N separate deployables. Revisit only if a specific domain's load genuinely requires independent scaling.

---

## 17. Final Product Vision

`implementation1.md` alone produces a strong, production-ready **multi-tenant help desk**: reliable ticket handling, SLA-governed, automation-driven, richly integrated (email, webhooks, AI-assisted replies), reportable, and hardened for real deployment (Redis, object storage, horizontal worker scaling, observability).

`implementation1.md + implementation2.md` together produce something categorically different: a **Service Desk / ITSM platform** with the domain depth enterprise buyers and IT operations teams actually expect. Concretely, the combined system can:

- Detect a production issue **automatically from a monitoring alert** (Track Q), open a correlated **Incident** (Track E) with a commander and a live, dual-audience timeline, and **surface the recent Change** that likely caused it (Track G) — the full monitoring-to-resolution loop the original prompt's Section on DevOps integrations envisioned, now fully specified end-to-end rather than as a bullet point.
- Let a customer **browse a real service catalog** and request access/hardware/software through a structured, approved, task-tracked fulfillment workflow (Track I + J + N) instead of typing free text into a generic ticket form.
- Govern infrastructure change through a **real risk-scored, scheduled, plan-carrying Change process** (Track G) rather than a boolean approval checkbox, with a feedback loop back into incident correlation.
- Know **what it's actually supporting** — assets, their owners, their dependencies, their warranty/license status (Track H) — and use that knowledge for impact analysis.
- Turn recurring pain into permanent knowledge via **Problem Management** (Track F), closing the loop from symptom to root cause to prevention.
- Route work to the **right skilled, available person** (Track L), measure whether it was handled well (Track M), and know whether the customer's **contracted entitlement** (Track K) is being honored or exhausted.
- Handle security-sensitive incidents with **mandatory four-eyes approval and tamper-evident evidence** (Track P), and use **predictive, human-in-the-loop AI** (Track R) to flag breach risk and draft — never auto-publish — post-incident reviews.

Architecturally, the platform gains two foundational engines — a **transactional-outbox event backbone** (Track O) and a **durable workflow orchestration runtime** (Track N) — that every domain above shares, rather than each domain inventing its own async/approval machinery. This is the structural difference between "a pile of ITSM-flavored features bolted onto a ticket table" and "a service desk platform with a coherent domain model and a reusable execution substrate," and it is the primary reason this plan sequences Tracks N and O before any domain feature that depends on them.