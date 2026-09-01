"use client";

import { useEffect, useState, useCallback } from "react";
import RequireAuth from "../components/RequireAuth";
import { hasPermission } from "../../lib/permissions";
import { useAuth } from "../../lib/auth-context";
import { api } from "../../lib/api";
import Button from "../components/ui/Button";
import EmptyState from "../components/ui/EmptyState";
import Input from "../components/ui/Input";
import PageHeader from "../components/ui/PageHeader";
import PageTransition from "../components/ui/PageTransition";
import Select from "../components/ui/Select";
import Spinner from "../components/ui/Spinner";
import { Card, ListPanel } from "../components/ui/Card";

function SlaPage() {
  const { user } = useAuth();
  const [policies, setPolicies] = useState([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  const [name, setName] = useState("");
  const [priority, setPriority] = useState("P3");
  const [firstResponse, setFirstResponse] = useState(30);
  const [resolutionHours, setResolutionHours] = useState(8);
  const [submitting, setSubmitting] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setPolicies(await api.listSlaPolicies());
    } catch (err) {
      setError(err.message || "Failed to load SLA policies");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function handleCreate(e) {
    e.preventDefault();
    setSubmitting(true);
    setError("");
    try {
      await api.createSlaPolicy({
        name,
        priority,
        first_response_minutes: Number(firstResponse),
        resolution_hours: Number(resolutionHours),
        is_active: true,
      });
      setName("");
      await load();
    } catch (err) {
      setError(err.message || "Failed to create policy");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <PageTransition className="mx-auto max-w-3xl px-4 py-8">
      <PageHeader title="SLA Policies" description="Define response and resolution targets by priority." />

      {error && <p className="mb-4 text-sm text-danger">{error}</p>}

      {loading ? (
        <Spinner label="Loading policies…" />
      ) : (
        <ListPanel className="mb-8">
          {policies.map((p) => (
            <div key={p.id} className="flex items-center justify-between px-4 py-3 text-sm">
              <div>
                <p className="font-medium text-foreground">{p.name}</p>
                <p className="text-xs text-muted-foreground">
                  {p.priority} · first response {p.first_response_minutes}m · resolve in {p.resolution_hours}h
                </p>
              </div>
              <span
                className={`rounded-full px-2.5 py-1 text-xs font-medium ${
                  p.is_active
                    ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300"
                    : "bg-muted text-muted-foreground"
                }`}
              >
                {p.is_active ? "Active" : "Inactive"}
              </span>
            </div>
          ))}
          {policies.length === 0 && <EmptyState>No policies yet.</EmptyState>}
        </ListPanel>
      )}

      {hasPermission(user, "sla.manage") && (
        <Card>
          <form onSubmit={handleCreate} className="space-y-3">
            <h2 className="text-sm font-medium text-foreground">Create policy</h2>
            <Input required placeholder="Name" value={name} onChange={(e) => setName(e.target.value)} />
            <div className="flex flex-wrap gap-3">
              <Select value={priority} onChange={(e) => setPriority(e.target.value)} className="rounded-full">
                {["P1", "P2", "P3", "P4"].map((p) => (
                  <option key={p} value={p}>
                    {p}
                  </option>
                ))}
              </Select>
              <Input
                type="number"
                min={1}
                value={firstResponse}
                onChange={(e) => setFirstResponse(e.target.value)}
                placeholder="First response (min)"
                className="w-40"
              />
              <Input
                type="number"
                min={1}
                value={resolutionHours}
                onChange={(e) => setResolutionHours(e.target.value)}
                placeholder="Resolution (hrs)"
                className="w-40"
              />
            </div>
            <Button type="submit" disabled={submitting}>
              {submitting ? "Creating…" : "Create policy"}
            </Button>
          </form>
        </Card>
      )}
    </PageTransition>
  );
}

export default function Page() {
  return (
    <RequireAuth permissions={["sla.view"]}>
      <SlaPage />
    </RequireAuth>
  );
}
