"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import RequireAuth from "../../components/RequireAuth";
import PageHeader from "../../components/ui/PageHeader";
import PageTransition from "../../components/ui/PageTransition";
import Spinner from "../../components/ui/Spinner";
import { ListPanel } from "../../components/ui/Card";
import { api } from "../../../lib/api";

function PortalTickets() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await api.listTickets({ page: 1, size: 20 });
      setItems(data.items);
    } catch (err) {
      setError(err.message || "Failed to load tickets");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <PageTransition className="mx-auto max-w-3xl px-4 py-8">
      <PageHeader
        title="My tickets"
        description="Track your support requests."
        action={
          <Link href="/portal/tickets/new" className="text-sm font-medium text-accent hover:underline">
            New ticket
          </Link>
        }
      />
      {error && <p className="mb-4 text-sm text-danger">{error}</p>}
      {loading ? (
        <Spinner />
      ) : (
        <ListPanel>
          {items.map((t) => (
            <Link key={t.id} href={`/tickets/${t.id}`} className="block px-4 py-3 text-sm hover:bg-muted">
              <span className="font-mono text-xs text-muted-foreground">{t.ticket_number}</span>
              <p className="font-medium text-foreground">{t.title}</p>
              <p className="text-xs text-muted-foreground">{t.status}</p>
            </Link>
          ))}
          {items.length === 0 && <p className="px-4 py-6 text-sm text-muted-foreground">No tickets yet.</p>}
        </ListPanel>
      )}
    </PageTransition>
  );
}

export default function Page() {
  return (
    <RequireAuth>
      <PortalTickets />
    </RequireAuth>
  );
}
