"use client";

import { useEffect, useState, useCallback } from "react";
import RequireAuth from "../../components/RequireAuth";
import { api } from "../../../lib/api";
import { formatAuditAction, formatEntityType } from "../../../lib/format";
import EmptyState from "../../components/ui/EmptyState";
import PageHeader from "../../components/ui/PageHeader";
import PageTransition from "../../components/ui/PageTransition";
import Pagination from "../../components/ui/Pagination";
import Spinner from "../../components/ui/Spinner";
import { ListPanel } from "../../components/ui/Card";

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
    <PageTransition className="mx-auto max-w-4xl px-4 py-8">
      <PageHeader title="Audit Log" description="Review system activity and changes." />
      {error && <p className="mb-4 text-sm text-danger">{error}</p>}
      {loading ? (
        <Spinner label="Loading audit log…" />
      ) : (
        <ListPanel>
          {items.map((log) => (
            <div key={log.id} className="px-4 py-3 text-sm">
              <div className="flex items-center justify-between">
                <span className="font-medium text-foreground">{formatAuditAction(log.action)}</span>
                <span className="text-xs text-muted-foreground">{new Date(log.created_at).toLocaleString()}</span>
              </div>
              <p className="mt-1 text-xs text-muted-foreground">
                {log.actor_name ? `By ${log.actor_name}` : ""}
                {log.actor_name && (log.entity_name || log.entity_type) ? " · " : ""}
                {formatEntityType(log.entity_type)}
                {log.entity_name ? ` · ${log.entity_name}` : ""}
              </p>
            </div>
          ))}
          {items.length === 0 && <EmptyState>No entries.</EmptyState>}
        </ListPanel>
      )}

      <Pagination page={page} totalPages={totalPages} onPageChange={setPage} />
    </PageTransition>
  );
}

export default function Page() {
  return (
    <RequireAuth permissions={["audit.view"]}>
      <AuditPage />
    </RequireAuth>
  );
}
