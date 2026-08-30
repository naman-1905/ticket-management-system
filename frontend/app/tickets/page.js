"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import RequireAuth from "../components/RequireAuth";
import StatusBadge from "../components/StatusBadge";
import PriorityBadge from "../components/PriorityBadge";
import { api } from "../../lib/api";

const STATUSES = ["OPEN", "IN_PROGRESS", "ON_HOLD", "RESOLVED", "CLOSED"];
const PRIORITIES = ["P1", "P2", "P3", "P4"];

function TicketsPage() {
  const [items, setItems] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [size] = useState(20);
  const [status, setStatus] = useState("");
  const [priority, setPriority] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const data = await api.listTickets({ page, size, status, priority });
      setItems(data.items);
      setTotal(data.total);
    } catch (err) {
      setError(err.message || "Failed to load tickets");
    } finally {
      setLoading(false);
    }
  }, [page, size, status, priority]);

  useEffect(() => {
    load();
  }, [load]);

  const totalPages = Math.max(1, Math.ceil(total / size));

  return (
    <div className="max-w-5xl mx-auto px-4 py-8">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-semibold">Tickets</h1>
        <Link
          href="/tickets/new"
          className="bg-slate-900 text-white text-sm font-medium px-4 py-2 rounded-md hover:bg-slate-800"
        >
          + New ticket
        </Link>
      </div>

      <div className="flex gap-3 mb-4">
        <select
          value={status}
          onChange={(e) => {
            setPage(1);
            setStatus(e.target.value);
          }}
          className="border border-slate-300 rounded-md px-3 py-2 text-sm bg-white"
        >
          <option value="">All statuses</option>
          {STATUSES.map((s) => (
            <option key={s} value={s}>
              {s.replace("_", " ")}
            </option>
          ))}
        </select>
        <select
          value={priority}
          onChange={(e) => {
            setPage(1);
            setPriority(e.target.value);
          }}
          className="border border-slate-300 rounded-md px-3 py-2 text-sm bg-white"
        >
          <option value="">All priorities</option>
          {PRIORITIES.map((p) => (
            <option key={p} value={p}>
              {p}
            </option>
          ))}
        </select>
      </div>

      {error && <p className="text-sm text-red-600 mb-4">{error}</p>}

      {loading ? (
        <p className="text-slate-500 text-sm">Loading tickets…</p>
      ) : items.length === 0 ? (
        <p className="text-slate-500 text-sm">No tickets found.</p>
      ) : (
        <div className="bg-white border border-slate-200 rounded-lg divide-y divide-slate-100">
          {items.map((t) => (
            <Link
              key={t.id}
              href={`/tickets/${t.id}`}
              className="flex items-center justify-between px-4 py-3 hover:bg-slate-50"
            >
              <div className="min-w-0">
                <div className="flex items-center gap-2 mb-0.5">
                  <span className="text-xs text-slate-400 font-mono">{t.ticket_number}</span>
                  <PriorityBadge priority={t.priority} />
                </div>
                <p className="font-medium text-slate-900 truncate">{t.title}</p>
              </div>
              <StatusBadge status={t.status} />
            </Link>
          ))}
        </div>
      )}

      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-3 mt-6 text-sm">
          <button
            disabled={page <= 1}
            onClick={() => setPage((p) => p - 1)}
            className="px-3 py-1 rounded-md border border-slate-300 disabled:opacity-40"
          >
            Previous
          </button>
          <span className="text-slate-500">
            Page {page} of {totalPages}
          </span>
          <button
            disabled={page >= totalPages}
            onClick={() => setPage((p) => p + 1)}
            className="px-3 py-1 rounded-md border border-slate-300 disabled:opacity-40"
          >
            Next
          </button>
        </div>
      )}
    </div>
  );
}

export default function Page() {
  return (
    <RequireAuth>
      <TicketsPage />
    </RequireAuth>
  );
}
