"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { Ticket, Inbox, CircleCheck, Archive, AlertTriangle, Timer, Activity, PieChart, BarChart3 } from "lucide-react";
import RequireAuth from "../components/RequireAuth";
import PageHeader from "../components/ui/PageHeader";
import PageTransition from "../components/ui/PageTransition";
import Spinner from "../components/ui/Spinner";
import { Card } from "../components/ui/Card";
import Tabs from "../components/ui/Tabs";
import AreaChart from "../components/charts/AreaChart";
import DonutChart from "../components/charts/DonutChart";
import PriorityBars from "../components/charts/PriorityBars";
import { STATUS_COLORS, AREA_SERIES } from "../components/charts/palette";
import { api } from "../../lib/api";
import { hasPermission } from "../../lib/permissions";
import { useAuth } from "../../lib/auth-context";

const CHART_TABS = [
  { key: "activity", label: "Activity", icon: Activity, color: "#0ea5e9" },
  { key: "status", label: "By Status", icon: PieChart, color: "#8b5cf6" },
  { key: "priority", label: "By Priority", icon: BarChart3, color: "#f97316" },
];

const CHART_META = {
  activity: { title: "Ticket activity", sub: "Created vs resolved · last 14 days" },
  status: { title: "By status", sub: "How tickets are distributed across their current status" },
  priority: { title: "By priority", sub: "Volume across P1 (critical) to P4 (low)" },
};

function formatHours(h) {
  if (h == null) return "—";
  if (h < 24) return `${Math.round(h)}h`;
  return `${(h / 24).toFixed(1)}d`;
}

function StatCard({ label, value, sub }) {
  return (
    <Card className="p-4">
      <div className="min-w-0">
        <p className="truncate text-xs font-medium text-muted-foreground">{label}</p>
        <p className="mt-1.5 text-2xl font-semibold tabular-nums text-foreground">{value}</p>
        {sub && <p className="mt-0.5 truncate text-xs text-muted-foreground">{sub}</p>}
      </div>
    </Card>
  );
}

function DashboardPage() {
  const { user } = useAuth();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [activeChart, setActiveChart] = useState("activity");

  const load = useCallback(async () => {
    if (!hasPermission(user, "report.view")) {
      setLoading(false);
      return;
    }
    setLoading(true);
    try {
      setData(await api.dashboardData());
    } catch (err) {
      setError(err.message || "Failed to load dashboard");
    } finally {
      setLoading(false);
    }
  }, [user]);

  useEffect(() => {
    load();
  }, [load]);

  const canView = hasPermission(user, "report.view");

  if (loading) {
    return (
      <PageTransition className="mx-auto max-w-6xl px-4 py-8">
        <Spinner label="Loading dashboard…" />
      </PageTransition>
    );
  }

  if (!canView || !data) {
    return (
      <PageTransition className="mx-auto max-w-6xl px-4 py-8">
        <PageHeader title="Dashboard" description={`Welcome back, ${user?.full_name || ""}.`} />
        {error && <p className="mb-4 text-sm text-danger">{error}</p>}
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
      </PageTransition>
    );
  }

  const statusData = (data.by_status || [])
    .map((s) => ({ label: s.status, value: s.count, color: STATUS_COLORS[s.status] || "#a8a29e" }))
    .sort((a, b) => b.value - a.value);

  const cards = [
    { icon: Ticket, label: "Total tickets", value: data.total_tickets, color: "#f97316" },
    { icon: Inbox, label: "Open", value: data.open_tickets, sub: `${data.unassigned} unassigned`, color: "#3b82f6" },
    { icon: CircleCheck, label: "Resolved", value: data.resolved_tickets, color: "#10b981" },
    { icon: Archive, label: "Closed", value: data.closed_tickets, color: "#78716c" },
    { icon: AlertTriangle, label: "SLA breached", value: data.sla_breached, color: "#ef4444" },
    { icon: Timer, label: "Avg resolution", value: formatHours(data.avg_resolution_hours), sub: "created → resolved", color: "#8b5cf6" },
  ];

  return (
    <PageTransition className="mx-auto max-w-6xl px-4 py-8">
      <PageHeader title="Dashboard" description={`Welcome back, ${user?.full_name || ""}.`} />

      {error && <p className="mb-4 text-sm text-danger">{error}</p>}

      <div className="grid grid-cols-2 gap-4 md:grid-cols-3 xl:grid-cols-6">
        {cards.map((c) => (
          <StatCard key={c.label} {...c} />
        ))}
      </div>

      <Card className="mt-4 p-5">
        <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h2 className="text-base font-semibold text-foreground">{CHART_META[activeChart].title}</h2>
            <p className="text-xs text-muted-foreground">{CHART_META[activeChart].sub}</p>
          </div>
          <Tabs options={CHART_TABS} value={activeChart} onChange={setActiveChart} />
        </div>

        {activeChart === "activity" && (
          <div className="mb-3 flex items-center gap-4">
            {AREA_SERIES.map((s) => (
              <span key={s.key} className="flex items-center gap-1.5 text-xs text-muted-foreground">
                <span className="inline-block h-2.5 w-2.5 rounded-full" style={{ background: s.color }} />
                {s.label}
              </span>
            ))}
          </div>
        )}

        {activeChart === "activity" && <AreaChart data={data.trend || []} />}
        {activeChart === "status" && <DonutChart data={statusData} />}
        {activeChart === "priority" && <PriorityBars data={data.by_priority || []} />}
      </Card>
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
