"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import RequireAuth from "../components/RequireAuth";
import PageHeader from "../components/ui/PageHeader";
import PageTransition from "../components/ui/PageTransition";
import Spinner from "../components/ui/Spinner";
import { Card } from "../components/ui/Card";
import { api } from "../../lib/api";
import { hasPermission } from "../../lib/permissions";
import { useAuth } from "../../lib/auth-context";

function DashboardPage() {
  const { user } = useAuth();
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    if (!hasPermission(user, "report.view")) {
      setLoading(false);
      return;
    }
    setLoading(true);
    try {
      setSummary(await api.reportSummary());
    } catch (err) {
      setError(err.message || "Failed to load dashboard");
    } finally {
      setLoading(false);
    }
  }, [user]);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <PageTransition className="mx-auto max-w-5xl px-4 py-8">
      <PageHeader title="Dashboard" description={`Welcome back, ${user?.full_name || ""}.`} />
      {error && <p className="mb-4 text-sm text-danger">{error}</p>}
      {loading ? (
        <Spinner label="Loading dashboard…" />
      ) : summary ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {[
            ["Open tickets", summary.open_tickets],
            ["Resolved", summary.resolved_tickets],
            ["Unassigned", summary.unassigned],
            ["SLA breached", summary.sla_breached],
          ].map(([label, value]) => (
            <Card key={label} className="p-4">
              <p className="text-xs text-muted-foreground">{label}</p>
              <p className="mt-1 text-2xl font-semibold text-foreground">{value}</p>
            </Card>
          ))}
        </div>
      ) : (
        <Card className="p-6">
          <p className="text-sm text-muted-foreground">Quick links</p>
          <div className="mt-4 flex flex-wrap gap-3">
            <Link href="/tickets" className="text-sm font-medium text-accent hover:underline">
              View tickets
            </Link>
            <Link href="/tickets/new" className="text-sm font-medium text-accent hover:underline">
              New ticket
            </Link>
          </div>
        </Card>
      )}
    </PageTransition>
  );
}

export default function Page() {
  return (
    <RequireAuth>
      <DashboardPage />
    </RequireAuth>
  );
}
