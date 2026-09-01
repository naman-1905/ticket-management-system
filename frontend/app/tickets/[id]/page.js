"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams } from "next/navigation";
import { motion } from "framer-motion";
import RequireAuth from "../../components/RequireAuth";
import StatusBadge from "../../components/StatusBadge";
import PriorityBadge from "../../components/PriorityBadge";
import Button from "../../components/ui/Button";
import PageTransition from "../../components/ui/PageTransition";
import Select from "../../components/ui/Select";
import Spinner from "../../components/ui/Spinner";
import Textarea from "../../components/ui/Textarea";
import { Card } from "../../components/ui/Card";
import { useAuth } from "../../../lib/auth-context";
import { api } from "../../../lib/api";

const STATUSES = ["OPEN", "IN_PROGRESS", "ON_HOLD", "RESOLVED", "CLOSED"];

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

  const canManage = user.role === "AGENT" || user.role === "ADMIN";

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [t, c, s] = await Promise.all([api.getTicket(id), api.listComments(id), api.getTicketSla(id)]);
      setTicket(t);
      setComments(c);
      setSla(s);
      if (canManage) setAgents(await api.listUsers("AGENT"));
    } catch (err) {
      setError(err.message || "Failed to load ticket");
    } finally {
      setLoading(false);
    }
  }, [id, canManage]);

  useEffect(() => {
    load();
  }, [load]);

  async function handleStatusChange(newStatus) {
    setStatusUpdating(true);
    setError("");
    try {
      setTicket(await api.updateTicketStatus(id, newStatus));
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
      setTicket(await api.assignTicket(id, assigneeId));
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
        <p className="mb-4 whitespace-pre-wrap text-sm text-muted-foreground">{ticket.description}</p>

        <div className="flex flex-wrap items-center gap-4 border-t border-border pt-4 text-sm">
          {canManage && (
            <Select
              label="Status"
              value={ticket.status}
              disabled={statusUpdating}
              onChange={(e) => handleStatusChange(e.target.value)}
              className="rounded-full px-3 py-1.5"
            >
              {STATUSES.map((s) => (
                <option key={s} value={s}>
                  {s.replace("_", " ")}
                </option>
              ))}
            </Select>
          )}

          {canManage && (
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
              <span className="text-xs text-muted-foreground">{new Date(c.created_at).toLocaleString()}</span>
              {c.is_internal && (
                <span className="text-xs font-medium text-amber-700 dark:text-amber-300">Internal note</span>
              )}
            </div>
            <p className="whitespace-pre-wrap text-foreground">{c.body}</p>
          </motion.div>
        ))}
      </div>

      <Card>
        <form onSubmit={handleAddComment} className="space-y-3">
          <Textarea
            rows={3}
            placeholder="Write a comment…"
            value={commentBody}
            onChange={(e) => setCommentBody(e.target.value)}
          />
          <div className="flex items-center justify-between">
            {canManage ? (
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
            <Button type="submit" disabled={posting}>
              {posting ? "Posting…" : "Add comment"}
            </Button>
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
