"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams } from "next/navigation";
import RequireAuth from "../../components/RequireAuth";
import StatusBadge from "../../components/StatusBadge";
import PriorityBadge from "../../components/PriorityBadge";
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

  if (loading) return <div className="max-w-3xl mx-auto px-4 py-10 text-slate-500 text-sm">Loading…</div>;
  if (!ticket)
    return <div className="max-w-3xl mx-auto px-4 py-10 text-red-600 text-sm">{error || "Ticket not found"}</div>;

  return (
    <div className="max-w-3xl mx-auto px-4 py-8">
      {error && <p className="text-sm text-red-600 mb-4">{error}</p>}

      <div className="bg-white border border-slate-200 rounded-lg p-5 mb-6">
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs text-slate-400 font-mono">{ticket.ticket_number}</span>
          <div className="flex items-center gap-2">
            <PriorityBadge priority={ticket.priority} />
            <StatusBadge status={ticket.status} />
          </div>
        </div>
        <h1 className="text-xl font-semibold mb-2">{ticket.title}</h1>
        <p className="text-slate-600 whitespace-pre-wrap text-sm mb-4">{ticket.description}</p>

        <div className="flex flex-wrap items-center gap-4 text-sm border-t border-slate-100 pt-4">
          {canManage && (
            <div className="flex items-center gap-2">
              <label className="text-slate-500">Status:</label>
              <select
                value={ticket.status}
                disabled={statusUpdating}
                onChange={(e) => handleStatusChange(e.target.value)}
                className="border border-slate-300 rounded-md px-2 py-1 text-sm bg-white"
              >
                {STATUSES.map((s) => (
                  <option key={s} value={s}>
                    {s.replace("_", " ")}
                  </option>
                ))}
              </select>
            </div>
          )}

          {canManage && (
            <div className="flex items-center gap-2">
              <label className="text-slate-500">Assignee:</label>
              <select
                value={ticket.assignee_id || ""}
                disabled={assigning}
                onChange={(e) => handleAssign(e.target.value)}
                className="border border-slate-300 rounded-md px-2 py-1 text-sm bg-white"
              >
                <option value="">Unassigned</option>
                {agents.map((a) => (
                  <option key={a.id} value={a.id}>
                    {a.full_name}
                  </option>
                ))}
              </select>
            </div>
          )}

          {sla && sla.status !== "PENDING" && (
            <div className="text-slate-500">
              SLA: <span className="font-medium text-slate-700">{sla.status}</span>
              {sla.resolution_due_at && <> · due {new Date(sla.resolution_due_at).toLocaleString()}</>}
            </div>
          )}
        </div>
      </div>

      <h2 className="text-lg font-semibold mb-3">Comments</h2>
      <div className="space-y-3 mb-6">
        {comments.length === 0 && <p className="text-sm text-slate-500">No comments yet.</p>}
        {comments.map((c) => (
          <div
            key={c.id}
            className={`border rounded-lg p-3 text-sm ${
              c.is_internal ? "bg-amber-50 border-amber-200" : "bg-white border-slate-200"
            }`}
          >
            <div className="flex items-center justify-between mb-1">
              <span className="text-xs text-slate-400">{new Date(c.created_at).toLocaleString()}</span>
              {c.is_internal && <span className="text-xs font-medium text-amber-700">Internal note</span>}
            </div>
            <p className="whitespace-pre-wrap text-slate-700">{c.body}</p>
          </div>
        ))}
      </div>

      <form onSubmit={handleAddComment} className="bg-white border border-slate-200 rounded-lg p-4 space-y-3">
        <textarea
          rows={3}
          placeholder="Write a comment…"
          value={commentBody}
          onChange={(e) => setCommentBody(e.target.value)}
          className="w-full border border-slate-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-slate-900"
        />
        <div className="flex items-center justify-between">
          {canManage ? (
            <label className="flex items-center gap-2 text-sm text-slate-600">
              <input type="checkbox" checked={isInternal} onChange={(e) => setIsInternal(e.target.checked)} />
              Internal note (not visible to customer)
            </label>
          ) : (
            <span />
          )}
          <button
            type="submit"
            disabled={posting}
            className="bg-slate-900 text-white rounded-md px-4 py-2 text-sm font-medium hover:bg-slate-800 disabled:opacity-50"
          >
            {posting ? "Posting…" : "Add comment"}
          </button>
        </div>
      </form>
    </div>
  );
}

export default function Page() {
  return (
    <RequireAuth>
      <TicketDetail />
    </RequireAuth>
  );
}
