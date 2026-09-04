"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Plus } from "lucide-react";
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
import Input from "../components/ui/Input";
import { api } from "../../lib/api";
import { TICKET_STATUSES, TICKET_PRIORITIES } from "../../lib/constants";
import { formatStatus } from "../../lib/format";

function TicketsPage() {
  const [items, setItems] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [size] = useState(20);
  const [status, setStatus] = useState("");
  const [priority, setPriority] = useState("");
  const [search, setSearch] = useState("");
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const timer = setTimeout(() => {
      setQuery(search.trim());
      setPage(1);
    }, 300);
    return () => clearTimeout(timer);
  }, [search]);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const data = await api.listTickets({ page, size, status, priority, q: query });
        if (!cancelled) {
          setItems(data.items);
          setTotal(data.total);
          setError("");
        }
      } catch (err) {
        if (!cancelled) setError(err.message || "Failed to load tickets");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => { cancelled = true; };
  }, [page, size, status, priority, query]);

  const totalPages = Math.max(1, Math.ceil(total / size));

  return (
    <PageTransition className="mx-auto max-w-5xl px-4 py-8">
      <PageHeader
        title="Tickets"
        description="Track and manage support requests."
        action={
          <Link href="/tickets/new">
            <Button className="gap-1.5">
              <Plus className="h-4 w-4" strokeWidth={2} />
              New ticket
            </Button>
          </Link>
        }
      />

      <div className="mb-4 flex flex-wrap items-end gap-3">
        <Input
          label="Search"
          placeholder="Search by number, title, description…"
          aria-label="Search tickets"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="min-w-[240px] flex-1"
        />
        <Select
          value={status}
          onChange={(e) => {
            setPage(1);
            setStatus(e.target.value);
          }}
          className="rounded-full px-4"
        >
          <option value="">All statuses</option>
          {TICKET_STATUSES.map((s) => (
            <option key={s} value={s}>
              {formatStatus(s)}
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
          {TICKET_PRIORITIES.map((p) => (
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
                  {t.assignee_name && (
                    <p className="truncate text-xs text-muted-foreground">Assigned to {t.assignee_name}</p>
                  )}
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
