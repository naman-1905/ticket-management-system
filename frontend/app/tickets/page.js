"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import RequireAuth from "../components/RequireAuth";
import StatusBadge from "../components/StatusBadge";
import PriorityBadge from "../components/PriorityBadge";
import Button from "../components/ui/Button";
import EmptyState from "../components/ui/EmptyState";
import PageHeader from "../components/ui/PageHeader";
import PageTransition from "../components/ui/PageTransition";
import Pagination from "../components/ui/Pagination";
import Select from "../components/ui/Select";
import Spinner from "../components/ui/Spinner";
import { ListPanel } from "../components/ui/Card";
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
    <PageTransition className="mx-auto max-w-5xl px-4 py-8">
      <PageHeader
        title="Tickets"
        description="Track and manage support requests."
        action={
          <Link href="/tickets/new">
            <Button>+ New ticket</Button>
          </Link>
        }
      />

      <div className="mb-4 flex flex-wrap gap-3">
        <Select
          value={status}
          onChange={(e) => {
            setPage(1);
            setStatus(e.target.value);
          }}
          className="rounded-full px-4"
        >
          <option value="">All statuses</option>
          {STATUSES.map((s) => (
            <option key={s} value={s}>
              {s.replace("_", " ")}
            </option>
          ))}
        </Select>
        <Select
          value={priority}
          onChange={(e) => {
            setPage(1);
            setPriority(e.target.value);
          }}
          className="rounded-full px-4"
        >
          <option value="">All priorities</option>
          {PRIORITIES.map((p) => (
            <option key={p} value={p}>
              {p}
            </option>
          ))}
        </Select>
      </div>

      {error && <p className="mb-4 text-sm text-danger">{error}</p>}

      {loading ? (
        <Spinner label="Loading tickets…" />
      ) : items.length === 0 ? (
        <EmptyState>No tickets found.</EmptyState>
      ) : (
        <ListPanel>
          {items.map((t) => (
            <motion.div key={t.id} whileHover={{ backgroundColor: "var(--muted)" }} transition={{ duration: 0.15 }}>
              <Link href={`/tickets/${t.id}`} className="flex items-center justify-between px-4 py-3">
                <div className="min-w-0">
                  <div className="mb-0.5 flex items-center gap-2">
                    <span className="font-mono text-xs text-muted-foreground">{t.ticket_number}</span>
                    <PriorityBadge priority={t.priority} />
                  </div>
                  <p className="truncate font-medium text-foreground">{t.title}</p>
                </div>
                <StatusBadge status={t.status} />
              </Link>
            </motion.div>
          ))}
        </ListPanel>
      )}

      <Pagination page={page} totalPages={totalPages} onPageChange={setPage} />
    </PageTransition>
  );
}

export default function Page() {
  return (
    <RequireAuth>
      <TicketsPage />
    </RequireAuth>
  );
}
