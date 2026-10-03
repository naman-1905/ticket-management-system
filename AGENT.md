# Agent Work Log (Qwen)

> **Author**: Qwen (coder). **Reader**: Codex (supervisor).
> **DO NOT COMMIT** unless Codex writes `COMMIT APPROVED` in `IMPROVEMENTS.md`.

## Project Info

- **Repo**: `git@github.com:naman-1905/ticket-management-system.git`
- **Branch**: `main`
- **Path**: `/home/naman/Projects/ticket-management-system`

## Commit protocol (strict)

- After finishing a task, add a new session entry (at the top).
- Include a **COMMIT REQUEST**.
- Wait for Codex to approve/block in `IMPROVEMENTS.md`.

## Test commands (run before requesting approval)

```bash
cd backend && .venv/bin/python -m pytest
cd frontend && npm run lint
cd frontend && npm run build
```

## Session template

```markdown
## Session: [YYYY-MM-DD HH:MM]

### Task
[Copy from INSTRUCTIONS.md]

### Status
In Progress | Completed | Blocked

### Files Modified
- `path/to/file` — [what changed]

### Notes
- [Key decisions / edge cases]

### Manual QA
- [Routes clicked]

## COMMIT REQUEST

### Changes Made
- `path/to/file` — [what changed]

### Tests
- [ ] Backend: `.venv/bin/python -m pytest` (result)
- [ ] Frontend: `npm run lint` (result)
- [ ] Frontend: `npm run build` (result)

### Ready for Verification
Please verify and approve commit in `IMPROVEMENTS.md`.
```

---

## Historical notes

The previous long-form implementation log was archived to `AGENT_HISTORY.md`. Ignore everything below this line.

---

# AGENT.md — Implementation Session Log

This file is a working log for the agent implementing `IMPLEMENTATION_PLAN.md`. It is not
part of the product; keep it out of review-focused diffs (it sits at repo root next to the plan).

## Environment assumptions

- Work happens in `/home/naman/Projects/ticket-management-system` (branch: main).
- Backend venv: `backend/.venv` (Python 3.10, FastAPI + SQLAlchemy async + asyncpg).
- Frontend: Next.js 16 (App Router) + React 19, Tailwind v4, no test runner yet.
- Postgres runs **locally** on this machine (`127.0.0.1:5432`). The original `backend/.env`
  pointed at `192.168.1.38`, which is unreachable from this host, so `.env` was updated to
  `127.0.0.1` (gitignored local file). Databases: `ticketing_db` (dev, schema created via
  `python -m scripts.bootstrap_db`) and `ticketing_db_test` (created for tests; role `naman`
  was granted CREATEDB).
- Test DB URL used by pytest:
  `TEST_DATABASE_URL=postgresql+asyncpg://naman:Naman%401905_1650@127.0.0.1:5432/ticketing_db_test`
  (default in `test_api.py` uses password `naman`, which does not match this host).

## Validation commands

```bash
# Backend tests (DB required)
cd backend && TEST_DATABASE_URL='postgresql+asyncpg://naman:Naman%401905_1650@127.0.0.1:5432/ticketing_db_test' .venv/bin/python -m pytest

# Frontend
cd frontend && npm run lint
cd frontend && npm run build
```

## Pre-change baseline (recorded before any edits)

### Backend — `pytest` → 28 passed, 5 failed (all pre-existing)

1. `tests/test_api.py::test_ticket_creation_idempotency`
   - Root cause: **real bug**. Idempotent replay returns the cached dict produced by
     `ticket_to_dict()`, which omits `tenant_id`; `response_model=TicketOut` then fails
     validation → 500 on every replayed `POST /tickets` with an `Idempotency-Key`.
2. `tests/test_events.py` × 4 (`test_relay_delivers_and_marks_published`,
   `test_relay_schedules_retry_on_failure`, `test_relay_dead_letters_after_max_attempts`,
   `test_events_and_dead_letter_endpoints`)
   - Root cause: **test bug**. Tests emit `ticket.created` with payload `{"ticket_id": "x"}`,
     but `REQUIRED_PAYLOAD_KEYS["ticket.created"]` requires `ticket_number` too → 500
     `INVALID_EVENT_PAYLOAD`.

### Frontend — `npm run build` → PASS (16 routes)

### Frontend — `npm run lint` → FAIL, 9 pre-existing errors

All are `react-hooks/set-state-in-effect` (eslint-plugin-react-hooks v7.1.1, new in
eslint-config-next 16). The rule flags any synchronous `setState` inside an effect body,
including through called functions whose first statements set state before the first `await`.

Files: `app/admin/audit/page.js:36`, `app/admin/users/page.js:31`, `app/customers/page.js:48`,
`app/dashboard/page.js:36`, `app/portal/tickets/page.js:30`, `app/sla/page.js:41`,
`app/tickets/[id]/page.js:60`, `app/tickets/page.js:59`, `lib/theme-context.js:21`.

**Verified compliant pattern** (probed with scratch files through the real eslint config):

```js
useEffect(() => {
  let cancelled = false;
  async function load() {
    try {
      const data = await api.something();   // no setState before this first await
      if (!cancelled) setItems(data.items);
    } catch (err) {
      if (!cancelled) setError(err.message || "Failed to load");
    } finally {
      if (!cancelled) setLoading(false);
    }
  }
  load();
  return () => { cancelled = true; };
}, [deps]);
```

Pattern that FAILS: `setLoading(true)` as the first statement of the async loader called from
the effect. Consequence accepted: refetches (filter changes) no longer flash a spinner until
data arrives (stale-while-revalidate); initial load still shows the spinner via
`useState(true)`.

## Baseline fixes (done before Phase 1, to make "existing tests pass" achievable)

- [x] `backend/app/services/tickets.py`: added `tenant_id` to `ticket_to_dict()` (fixes idempotent replay 500).
- [x] `backend/tests/test_events.py`: emit full payloads (`ticket_number` added) in 4 tests.
- [x] `frontend/lib/theme-context.js`: rewritten with `useSyncExternalStore`; `mounted` derived
      via the server/client snapshot idiom (no setState-in-effect). Public API unchanged:
      `{ theme, setTheme, toggleTheme, mounted }`.

## Phase log

### Phase 1 — P0 fixes (done)

Tasks: TICK-UI-001, TICK-UI-002, TICK-UI-003, TICK-API-001, TICK-UI-004.

- [x] TICK-UI-001 `app/admin/users/page.js`: role dropdown now uses `ROLES` from
      `lib/constants.js` (was `"CUSTOMER ADMIN"` with a space → PATCH 422). Labels render
      via `r.replace(/_/g, " ")`.
- [x] TICK-UI-002: new `lib/constants.js` (`TICKET_STATUSES`, `TICKET_PRIORITIES`, `ROLES`);
      `formatStatus()` in `lib/format.js`; `StatusBadge` covers all 9 statuses; filter
      dropdowns in `app/tickets/page.js` use the shared constants.
- [x] TICK-UI-003: `lib/api.js` exposes `onSessionExpired(cb)`; unrecoverable 401 (no refresh
      token, or refresh rejected) fires it. `auth-context.js` registers a handler that clears
      user state → `RequireAuth` redirects to `/login?next=<path>`. Login page honors `next`
      (validated: starts with `/`, not `//`).
- [x] TICK-API-001: `GET /api/v1/attachments/{id}/download` in `routers/attachments.py` —
      tenant-scoped lookup, re-checks ticket visibility via `get_ticket_for_user`, streams file
      with Content-Disposition, 410 GONE if the stored file is missing. Declared BEFORE
      `/tickets/{ticket_id}` (FastAPI order: `{attachment_id}/download` would otherwise never
      match). Test `test_attachment_download` added (200 + headers, 404 for no-access user,
      404 unknown id).
- [x] TICK-UI-004: `RequireAuth` now uses `hasPermission(user, p)` from `lib/permissions.js`
      instead of raw `user.permissions.includes(p)`, so `platform.admin` works.

Lint policy note: files touched in this phase were also converted to the compliant effect
pattern (`tickets/page.js`, `tickets/[id]/page.js`, `admin/users/page.js`). Remaining 5
set-state-in-effect errors (audit, customers, dashboard, portal/tickets, sla) are fixed in
their own phases.

Status: backend pytest 34/34 passed; frontend build OK; lint 5 errors left (later phases).

### Phase 2 — TICK-API-002: enrich outbound names (done)

Task: add `assignee_name` to `TicketOut`, `author_name` to `CommentOut`; batch-load users in
comment list. Acceptance: GET comments returns `author_name`; GET ticket returns `assignee_name`
when assigned.

- [x] `schemas.py`: `TicketOut.assignee_name: str | None = None`,
      `CommentOut.author_name: str | None = None`.
- [x] `routers/tickets.py`: `_ticket_out(db, ticket, user)` is now async — resolves the assignee's
      `full_name` (single lookup when assigned) and delegates to `_ticket_out_sync(...)`, which
      builds `TicketOut` with `assignee_name`. All single-ticket call sites (create, transition,
      legacy status PATCH, assign, detail GET) `await _ticket_out(db, ticket, user)`. List + search
      endpoints use `[await _ticket_out(db, t, user) for t in rows]`.
- [x] Comment GET endpoint batch-loads author names (`User.id`/`full_name` IN query) and returns
      enriched `CommentOut`; comment POST returns an enriched comment via `_comment_out(...)`.
      Internal-comment visibility gating (`comment.internal.read`) is unchanged.
- [x] `routers/search.py`: updated to `await _ticket_out(db, t, user)` for the new async signature.
- [x] New test `tests/test_api.py::test_enriched_outbound_names`: unassigned ticket →
      `assignee_name: null`; POST comment returns `author_name`; after assigning an AGENT, assign /
      detail / list all return the agent's name; comments GET returns correct `author_name`.

Status: backend pytest 35/35 passed (was 34 + 1 new); frontend build OK; eslint clean on changed
files. Frontend now consumes the fields:
- `app/tickets/[id]/page.js`: header shows "Assigned to {assignee_name}" when set; each comment card
  shows `author_name` (falls back to "Unknown") next to the timestamp.
- `app/tickets/page.js`: list rows show "Assigned to {assignee_name}" when set.

Remaining Phase 2 (TICK-UI-010…013): detail layout split, attachment upload/list/download wiring,
consolidated parallel data loading, SLA urgency styling — not yet started.

### Gmail Sync + Google OAuth + LLM Ticket Creation (notes.md plan)

Task: Implement Google OAuth login, Gmail email syncing, LLM-based ticket creation, and frontend wiring per `notes.md`.

#### Backend changes

- [x] `app/config.py`: Added `google_client_id`, `google_client_secret`, `google_redirect_uri`,
      `llm_api_url`, `llm_model`, `llm_api_key`, `email_sync_interval_seconds` settings.
- [x] `requirements.txt`: Added `google-auth`, `google-api-python-client`, `httpx`.
- [x] `app/models/__init__.py`: Added `GoogleToken`, `EmailSyncState`, `SyncedEmail` models.
- [x] `alembic/versions/004_gmail_sync.py`: Migration for the three new tables (depends on `003_projects`).
- [x] `app/routers/google_auth.py`:
  - `GET /api/v1/auth/google/login` → returns Google OAuth authorization URL.
  - `GET /api/v1/auth/google/callback?code=...` → exchanges code, verifies ID token, upserts
    user/tenant, stores Google tokens, ensures sync state, issues app JWTs (TokenOut).
- [x] `app/services/gmail_sync.py`:
  - `_get_gmail_service()` — Gmail API client helper.
  - `refresh_google_token()` — refreshes expired access tokens via Google OAuth2 token endpoint.
  - `fetch_new_emails()` — lists unread emails from last day, fetches raw MIME, parses
    subject/sender/body.
  - `parse_email_to_ticket()` — calls LLM (OpenAI-compatible `/chat/completions`) to extract
    title/description/priority/category; falls back to basic email-derived fields on failure.
  - `sync_and_create_tickets()` — orchestrator: checks sync state, fetches new emails, skips
    already-processed Gmail message IDs, calls LLM extraction, creates tickets via existing
    `create_ticket` service with `source="EMAIL"`, inserts `SyncedEmail` records, updates
    `EmailSyncState.last_synced_at`. Returns count of tickets created.
- [x] `app/routers/gmail.py`:
  - `POST /api/v1/gmail/sync` — triggers immediate sync for current user.
  - `GET /api/v1/gmail/status` — returns connected/enabled/last_synced_at/emails_synced.
  - `PATCH /api/v1/gmail/settings` — enable/disable auto-sync.
- [x] `app/jobs/worker.py`: Added `process_email_sync()` to the worker loop — periodically syncs
      emails for all users with auto-sync enabled (respects `email_sync_interval_seconds`).
- [x] `app/main.py`: Mounted `google_auth` router at `/api/v1/auth` and `gmail` router at
      `/api/v1/gmail`.

#### Frontend changes

- [x] `lib/api.js`: Added `syncGmail()`, `getGmailStatus()`, `updateGmailSettings()`,
      `googleAuthLogin()`, `googleAuthCallback(code)` helpers.
- [x] `app/page.js`: Converted from redirect-only to a landing page with hero, feature grid,
      and CTA sections. Redirects authenticated users to their home page.
- [x] `app/components/Navbar.js`: Shows Login/Register buttons when unauthenticated instead of
      rendering nothing.
- [x] `app/login/page.js`: Added "Sign in with Google" button (Google SVG logo) below the
      password form, separated by an "Or continue with" divider. Calls `api.googleAuthLogin()`
      and redirects to the returned URL.
- [x] `app/auth/google/callback/page.js`: New page that reads `?code=...` from the query string,
      calls `api.googleAuthCallback(code)`, sets tokens, fetches `/me`, sets user state, and
      redirects to the appropriate home page. Shows spinner while processing, error message on
      failure with a "Back to login" link.
- [x] `app/tickets/page.js`: Added "Sync emails" button (RefreshCw icon) next to "New ticket" in
      the page header. Triggers `api.syncGmail()` then reloads the ticket list.

#### Config

- [x] `backend/.env.example`: Added `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`,
      `GOOGLE_REDIRECT_URI`, `LLM_API_URL`, `LLM_MODEL`, `LLM_API_KEY`,
      `EMAIL_SYNC_INTERVAL_SECONDS`.

#### Known limitations / next steps

- Google OAuth client ID/secret and redirect URI must be configured in `.env` before the
  Google login button will work (returns 503 if not set).
- Local LLM endpoint/model availability is unknown; the system falls back to basic
  email-derived fields if the LLM call fails.
- Migration `004_gmail_sync.py` has not been run yet (`alembic upgrade head`).
- No end-to-end OAuth or Gmail sync testing has been performed yet.
