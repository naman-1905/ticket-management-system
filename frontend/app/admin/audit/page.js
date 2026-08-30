"use client";

import { useEffect, useState, useCallback } from "react";
import RequireAuth from "../../components/RequireAuth";
import { api } from "../../../lib/api";

function AuditPage() {
  const [items, setItems] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [size] = useState(20);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await api.listAuditLogs({ page, size });
      setItems(data.items);
      setTotal(data.total);
    } catch (err) {
      setError(err.message || "Failed to load audit log");
    } finally {
      setLoading(false);
    }
  }, [page, size]);

  useEffect(() => {
    load();
  }, [load]);

  const totalPages = Math.max(1, Math.ceil(total / size));

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      <h1 className="text-2xl font-semibold mb-6">Audit Log</h1>
      {error && <p className="text-sm text-red-600 mb-4">{error}</p>}
      {loading ? (
        <p className="text-slate-500 text-sm">Loading…</p>
      ) : (
        <div className="bg-white border border-slate-200 rounded-lg divide-y divide-slate-100">
          {items.map((log) => (
            <div key={log.id} className="px-4 py-3 text-sm">
              <div className="flex items-center justify-between">
                <span className="font-medium">{log.action}</span>
                <span className="text-xs text-slate-400">{new Date(log.created_at).toLocaleString()}</span>
              </div>
              <p className="text-xs text-slate-500 mt-1">
                {log.entity_type} {log.entity_id ? `· ${log.entity_id}` : ""}
              </p>
            </div>
          ))}
          {items.length === 0 && <p className="px-4 py-3 text-sm text-slate-500">No entries.</p>}
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
    <RequireAuth roles={["ADMIN"]}>
      <AuditPage />
    </RequireAuth>
  );
}
