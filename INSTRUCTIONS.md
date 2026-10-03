# Current Instructions for Qwen

> Maintained by **Codex**. Qwen follows these instructions exactly.

---

## Project Info

- **Repo**: `git@github.com:naman-1905/ticket-management-system.git`
- **Branch**: `main`
- **Path**: `/home/naman/Projects/ticket-management-system`

---

## CRITICAL: Commit Protocol

You **cannot** commit or push unless Codex writes **`COMMIT APPROVED`** in `IMPROVEMENTS.md` with an explicit commit message and commands.

After you finish the task:
1. Update `AGENT.md` with what you did
2. Add a `## COMMIT REQUEST` section (see `AGENT.md` template)
3. Wait for Codex decision in `IMPROVEMENTS.md`

---

## Active Task: TICK-UI-010 — Ticket detail layout refactor

**Source of truth**: `IMPLEMENTATION_PLAN.md` (see “TICK-UI-010: Ticket detail layout refactor”)

### Goal

Refactor the staff ticket detail page into a clearer component structure so subsequent tasks (attachments, SLA urgency styling, parallel loading) are easy and safe.

### Scope (only this)

Work in the existing page:

- `frontend/app/tickets/[id]/page.js`

Split into components (create files under `frontend/app/components/` or `frontend/app/components/tickets/`):

- `TicketDetailHeader` — title, status, priority, assignee name, key actions
- `TicketDetailSidebar` — metadata summary (requester/org, created/updated, SLA summary placeholder)
- `TicketCommentThread` — comments list + composer
- `TicketAttachmentPanel` — placeholder UI only (no wiring yet; just layout)

**Do not implement** attachment upload/download wiring yet (that is TICK-UI-011).

### Requirements

- Keep the existing behavior intact (no regressions)
- No API contract changes
- Keep diffs minimal: just refactor and move UI blocks into components
- Preserve permission gating and existing conditional UI behavior

### Acceptance criteria

- [ ] `frontend/app/tickets/[id]/page.js` becomes a thin orchestrator that composes the new components
- [ ] UI renders exactly as before (same visible behavior)
- [ ] No new lint errors from `npm run lint`
- [ ] `npm run build` succeeds
- [ ] Manual QA: open a ticket detail page and verify header, sidebar, comments render and actions still work

### Commands to run (before COMMIT REQUEST)

```bash
cd /home/naman/Projects/ticket-management-system

cd backend && .venv/bin/python -m pytest
cd ../frontend && npm run lint
cd ../frontend && npm run build
```

If DB is required locally, set `TEST_DATABASE_URL` via env var (do not commit secrets).

---

## After completion

1. Update `AGENT.md` with a new session entry and **COMMIT REQUEST**
2. Wait for Codex to approve/block in `IMPROVEMENTS.md`

