"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { motion } from "framer-motion";
import { XCircle } from "lucide-react";
import RequireAuth from "../../components/RequireAuth";
import StatusBadge from "../../components/StatusBadge";
import PriorityBadge from "../../components/PriorityBadge";
import Button from "../../components/ui/Button";
import Input from "../../components/ui/Input";
import PageTransition from "../../components/ui/PageTransition";
import Select from "../../components/ui/Select";
import Spinner from "../../components/ui/Spinner";
import Textarea from "../../components/ui/Textarea";
import { Card } from "../../components/ui/Card";
import CSATWidget from "../../components/CSATWidget";
import { useAuth } from "../../../lib/auth-context";
import { api } from "../../../lib/api";
import { formatStatus, formatCategory, formatDate } from "../../../lib/format";
import { TICKET_CATEGORIES } from "../../../lib/constants";

import { hasPermission } from "../../../lib/permissions";

function toLocalInput(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  if (isNaN(d.getTime())) return "";
  const pad = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function TicketDetail() {
  const { id } = useParams();
  const { user } = useAuth();
  const [ticket, setTicket] = useState(null);
  const [comments, setComments] = useState([]);
  const [sla, setSla] = useState(null);
  const [agents, setAgents] = useState([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  const [commentBody, setCommentBody] = useState("");
  const [isInternal, setIsInternal] = useState(false);
  const [posting, setPosting] = useState(false);
  const [statusUpdating, setStatusUpdating] = useState(false);
  const [assigning, setAssigning] = useState(false);
  const [closing, setClosing] = useState(false);
  const [macros, setMacros] = useState([]);
  const [projects, setProjects] = useState([]);
  const [editCategory, setEditCategory] = useState("");
  const [editProjectId, setEditProjectId] = useState("");
  const [editDueAt, setEditDueAt] = useState("");
  const [savingMeta, setSavingMeta] = useState(false);

  const canManage = hasPermission(user, "ticket.transition") || hasPermission(user, "ticket.assign");
  const canInternal = hasPermission(user, "comment.internal.write");
  const canEditMeta = hasPermission(user, "ticket.update");

  useEffect(() => {
    let cancelled = false;
    async function initialLoad() {
      try {
        const [t, c, s] = await Promise.all([api.getTicket(id), api.listComments(id), api.getTicketSla(id)]);
        if (!cancelled) {
          setTicket(t);
          setComments(c);
          setSla(s);
          setError("");
        }
        if (!cancelled && hasPermission(user, "ticket.assign")) setAgents(await api.listAgents());
      } catch (err) {
        if (!cancelled) setError(err.message || "Failed to load ticket");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    initialLoad();
    return () => { cancelled = true; };
  }, [id, user]);

  useEffect(() => {
    api.listMacros().then(setMacros).catch(() => {});
  }, []);

  useEffect(() => {
    if (canEditMeta) api.listProjects().then(setProjects).catch(() => {});
  }, [canEditMeta]);

  // Initialise the metadata edit fields when a ticket is loaded.
  useEffect(() => {
    if (!ticket) return;
    setEditCategory(ticket.category || "");
    setEditProjectId(ticket.project_id || "");
    setEditDueAt(toLocalInput(ticket.due_at));
  }, [ticket?.id]);

  async function handleStatusChange(newStatus) {
    setStatusUpdating(true);
    setError("");
    try {
      const updated = ticket.allowed_transitions?.length
        ? await api.transitionTicket(id, newStatus, ticket.version)
        : await api.updateTicketStatus(id, newStatus);
      setTicket(updated);
    } catch (err) {
      setError(err.message || "Failed to update status");
    } finally {
      setStatusUpdating(false);
    }
  }

  async function handleAssign(assigneeId) {
    if (!assigneeId) return;
    setAssigning(true);
    setError("");
    try {
      setTicket(await api.assignTicket(id, { assignee_id: assigneeId }));
    } catch (err) {
      setError(err.message || "Failed to assign ticket");
    } finally {
      setAssigning(false);
    }
  }

  async function handleAddComment(e) {
    e.preventDefault();
    if (!commentBody.trim()) return;
    setPosting(true);
    setError("");
    try {
      const comment = await api.addComment(id, { body: commentBody, is_internal: isInternal });
      setComments((prev) => [...prev, comment]);
      setCommentBody("");
      setIsInternal(false);
    } catch (err) {
      setError(err.message || "Failed to add comment");
    } finally {
      setPosting(false);
    }
  }

  async function handleCloseTicket() {
    if (!confirm("Close this ticket? The customer will be notified.")) return;
    setClosing(true);
    setError("");
    try {
      const updated = ticket.allowed_transitions?.length
        ? await api.transitionTicket(id, "CLOSED", ticket.version)
        : await api.updateTicketStatus(id, "CLOSED");
      setTicket(updated);
    } catch (err) {
      setError(err.message || "Failed to close ticket");
    } finally {
      setClosing(false);
    }
  }

  async function handleSaveMeta() {
    setSavingMeta(true);
    setError("");
    try {
      const payload = {
        category: editCategory || null,
        project_id: editProjectId || null,
        due_at: editDueAt ? new Date(editDueAt).toISOString() : null,
      };
      const updated = await api.updateTicket(id, payload);
      setTicket(updated);
    } catch (err) {
      setError(err.message || "Failed to update details");
    } finally {
      setSavingMeta(false);
    }
  }

  if (loading) {
    return (
      <PageTransition className="mx-auto max-w-3xl px-4 py-10">
        <Spinner />
      </PageTransition>
    );
  }

  if (!ticket) {
    return (
      <PageTransition className="mx-auto max-w-3xl px-4 py-10">
        <p className="text-sm text-danger">{error || "Ticket not found"}</p>
      </PageTransition>
    );
  }

  return (
    <PageTransition className="mx-auto max-w-3xl px-4 py-8">
      {error && <p className="mb-4 text-sm text-danger">{error}</p>}

      <Card className="mb-6">
        <div className="mb-2 flex items-center justify-between">
          <span className="font-mono text-xs text-muted-foreground">{ticket.ticket_number}</span>
          <div className="flex items-center gap-2">
            <PriorityBadge priority={ticket.priority} />
            <StatusBadge status={ticket.status} />
          </div>
        </div>
        <h1 className="mb-2 text-xl font-semibold tracking-tight text-foreground">{ticket.title}</h1>
        {ticket.assignee_name && (
          <p className="mb-3 text-sm text-muted-foreground">
            Assigned to <span className="font-medium text-foreground">{ticket.assignee_name}</span>
          </p>
        )}
        <p className="mb-4 whitespace-pre-wrap text-sm text-muted-foreground">{ticket.description}</p>

        <div className="flex flex-wrap items-center gap-4 border-t border-border pt-4 text-sm">
          {canManage && ticket.allowed_transitions?.length > 0 && (
            <Select
              label="Status"
              value={ticket.status}
              disabled={statusUpdating}
              onChange={(e) => handleStatusChange(e.target.value)}
              className="rounded-full px-3 py-1.5"
            >
              <option value={ticket.status}>{formatStatus(ticket.status)}</option>
              {ticket.allowed_transitions.map((s) => (
                <option key={s} value={s}>
                  {formatStatus(s)}
                </option>
              ))}
            </Select>
          )}

          {hasPermission(user, "ticket.assign") && (
            <Select
              label="Assignee"
              value={ticket.assignee_id || ""}
              disabled={assigning}
              onChange={(e) => handleAssign(e.target.value)}
              className="rounded-full px-3 py-1.5"
            >
              <option value="">Unassigned</option>
              {agents.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.full_name}
                </option>
              ))}
            </Select>
          )}

          {sla && sla.status !== "PENDING" && (
            <div className="text-muted-foreground">
              SLA: <span className="font-medium text-foreground">{sla.status}</span>
              {sla.resolution_due_at && <> · due {new Date(sla.resolution_due_at).toLocaleString()}</>}
            </div>
          )}
        </div>
      </Card>

      <Card className="mb-6">
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-sm font-semibold tracking-tight text-foreground">Details</h2>
          {canEditMeta && (
            <Button type="button" variant="secondary" onClick={handleSaveMeta} disabled={savingMeta}>
              {savingMeta ? "Saving…" : "Save details"}
            </Button>
          )}
        </div>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <div>
            {canEditMeta ? (
              <Select label="Category" value={editCategory} onChange={(e) => setEditCategory(e.target.value)}>
                <option value="">No category</option>
                {TICKET_CATEGORIES.map((c) => (
                  <option key={c.value} value={c.value}>
                    {c.label}
                  </option>
                ))}
              </Select>
            ) : (
              <>
                <span className="mb-1.5 block text-sm font-medium text-muted-foreground">Category</span>
                <p className="text-sm text-foreground">{formatCategory(ticket.category) || "—"}</p>
              </>
            )}
          </div>
          <div>
            {canEditMeta ? (
              <Select label="Project" value={editProjectId} onChange={(e) => setEditProjectId(e.target.value)}>
                <option value="">No project</option>
                {projects.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name}
                  </option>
                ))}
              </Select>
            ) : (
              <>
                <span className="mb-1.5 block text-sm font-medium text-muted-foreground">Project</span>
                <p className="text-sm text-foreground">{ticket.project_name || "—"}</p>
              </>
            )}
          </div>
          <div>
            {canEditMeta ? (
              <Input label="Deadline" type="datetime-local" value={editDueAt} onChange={(e) => setEditDueAt(e.target.value)} />
            ) : (
              <>
                <span className="mb-1.5 block text-sm font-medium text-muted-foreground">Deadline</span>
                <p className="text-sm text-foreground">{formatDate(ticket.due_at) || "—"}</p>
              </>
            )}
          </div>
        </div>
      </Card>

      {(ticket.status === "RESOLVED" || ticket.status === "CLOSED") && (
        <CSATWidget ticketId={id} />
      )}

      <h2 className="mb-3 text-lg font-semibold tracking-tight text-foreground">Comments</h2>
      <div className="mb-6 space-y-3">
        {comments.length === 0 && <p className="text-sm text-muted-foreground">No comments yet.</p>}
        {comments.map((c, i) => (
          <motion.div
            key={c.id}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.04, duration: 0.25 }}
            className={`rounded-2xl border p-3 text-sm ${
              c.is_internal
                ? "border-amber-300/50 bg-amber-50 dark:border-amber-800 dark:bg-amber-950/30"
                : "border-border bg-surface"
            }`}
          >
            <div className="mb-1 flex items-center justify-between">
              <span className="text-xs font-medium text-foreground">{c.author_name || "Unknown"}</span>
              <span className="text-xs text-muted-foreground">{new Date(c.created_at).toLocaleString()}</span>
            </div>
            {c.is_internal && (
              <div className="mb-1">
                <span className="text-xs font-medium text-amber-700 dark:text-amber-300">Internal note</span>
              </div>
            )}
            <p className="whitespace-pre-wrap text-foreground">{c.body}</p>
          </motion.div>
        ))}
      </div>

      <Card>
        <form onSubmit={handleAddComment} className="space-y-3">
          {macros.length > 0 && (
            <Select
              label="Insert a macro"
              value=""
              onChange={(e) => {
                const m = macros.find((x) => x.id === e.target.value);
                if (m) setCommentBody(m.reply_body || "");
              }}
            >
              <option value="">Choose a canned reply…</option>
              {macros.map((m) => (
                <option key={m.id} value={m.id}>
                  {m.name}
                </option>
              ))}
            </Select>
          )}
          <Textarea
            rows={3}
            placeholder="Write a comment…"
            value={commentBody}
            onChange={(e) => setCommentBody(e.target.value)}
          />
          <div className="flex items-center justify-between">
            {canInternal ? (
              <label className="flex items-center gap-2 text-sm text-muted-foreground">
                <input
                  type="checkbox"
                  checked={isInternal}
                  onChange={(e) => setIsInternal(e.target.checked)}
                  className="rounded border-border accent-accent"
                />
                Internal note (not visible to customer)
              </label>
            ) : (
              <span />
            )}
            <div className="flex items-center gap-2">
              {hasPermission(user, "ticket.transition") && ticket.status !== "CLOSED" && (
                <Button
                  type="button"
                  variant="secondary"
                  onClick={handleCloseTicket}
                  disabled={closing}
                  className="gap-1.5"
                >
                  <XCircle size={16} strokeWidth={2} />
                  {closing ? "Closing…" : "Close ticket"}
                </Button>
              )}
              <Button type="submit" disabled={posting}>
                {posting ? "Posting…" : "Add comment"}
              </Button>
            </div>
          </div>
        </form>
      </Card>
    </PageTransition>
  );
}

export default function Page() {
  return (
    <RequireAuth>
      <TicketDetail />
    </RequireAuth>
  );
}
