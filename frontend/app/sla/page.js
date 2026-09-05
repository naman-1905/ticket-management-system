"use client";

import { useEffect, useState, useCallback } from "react";
import { Pencil, Trash2 } from "lucide-react";
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

  // Create form state
  const [name, setName] = useState("");
  const [priority, setPriority] = useState("P3");
  const [firstResponse, setFirstResponse] = useState(30);
  const [resolutionHours, setResolutionHours] = useState(8);
  const [submitting, setSubmitting] = useState(false);

  // Edit state
  const [editingId, setEditingId] = useState(null);
  const [editName, setEditName] = useState("");
  const [editPriority, setEditPriority] = useState("P3");
  const [editFirstResponse, setEditFirstResponse] = useState(30);
  const [editResolutionHours, setEditResolutionHours] = useState(8);
  const [savingEdit, setSavingEdit] = useState(false);
  const [deactivatingId, setDeactivatingId] = useState(null);

  const canManage = hasPermission(user, "sla.manage");

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
      setPriority("P3");
      setFirstResponse(30);
      setResolutionHours(8);
      await load();
    } catch (err) {
      setError(err.message || "Failed to create policy");
    } finally {
      setSubmitting(false);
    }
  }

  function startEdit(policy) {
    setEditingId(policy.id);
    setEditName(policy.name);
    setEditPriority(policy.priority);
    setEditFirstResponse(policy.first_response_minutes);
    setEditResolutionHours(policy.resolution_hours);
  }

  function cancelEdit() {
    setEditingId(null);
    setEditName("");
    setEditPriority("P3");
    setEditFirstResponse(30);
    setEditResolutionHours(8);
  }

  async function handleSaveEdit(policy) {
    setSavingEdit(true);
    setError("");
    try {
      await api.updateSlaPolicy(policy.id, {
        name: editName,
        priority: editPriority,
        first_response_minutes: Number(editFirstResponse),
        resolution_hours: Number(editResolutionHours),
        is_active: true,
      });
      cancelEdit();
      await load();
    } catch (err) {
      setError(err.message || "Failed to update policy");
    } finally {
      setSavingEdit(false);
    }
  }

  async function handleDeactivate(policy) {
    if (!confirm(`Deactivate policy "${policy.name}"? It will no longer apply to new tickets.`)) return;
    setDeactivatingId(policy.id);
    setError("");
    try {
      await api.updateSlaPolicy(policy.id, {
        name: policy.name,
        priority: policy.priority,
        first_response_minutes: policy.first_response_minutes,
        resolution_hours: policy.resolution_hours,
        is_active: false,
      });
      await load();
    } catch (err) {
      setError(err.message || "Failed to deactivate policy");
    } finally {
      setDeactivatingId(null);
    }
  }

  async function handleDelete(policy) {
    if (!confirm(`Permanently delete policy "${policy.name}"? This cannot be undone.`)) return;
    setError("");
    try {
      await api.deleteSlaPolicy(policy.id);
      cancelEdit();
      await load();
    } catch (err) {
      setError(err.message || "Failed to delete policy");
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
            <div key={p.id} className="px-4 py-3 text-sm">
              {editingId === p.id ? (
                /* ---- Edit mode ---- */
                <div className="space-y-3">
                  <div className="flex items-center gap-2">
                    <Input
                      required
                      value={editName}
                      onChange={(e) => setEditName(e.target.value)}
                      placeholder="Policy name"
                      className="flex-1"
                    />
                    <Select
                      value={editPriority}
                      onChange={(e) => setEditPriority(e.target.value)}
                      className="rounded-full w-24"
                    >
                      {["P1", "P2", "P3", "P4"].map((pr) => (
                        <option key={pr} value={pr}>
                          {pr}
                        </option>
                      ))}
                    </Select>
                  </div>
                  <div className="flex flex-wrap items-center gap-3">
                    <Input
                      type="number"
                      min={1}
                      value={editFirstResponse}
                      onChange={(e) => setEditFirstResponse(e.target.value)}
                      placeholder="First response (min)"
                      className="w-40"
                    />
                    <Input
                      type="number"
                      min={1}
                      value={editResolutionHours}
                      onChange={(e) => setEditResolutionHours(e.target.value)}
                      placeholder="Resolution (hrs)"
                      className="w-40"
                    />
                  </div>
                  <div className="flex items-center gap-2">
                    <Button
                      type="button"
                      onClick={() => handleSaveEdit(p)}
                      disabled={savingEdit}
                      className="text-xs px-3 py-1.5"
                    >
                      {savingEdit ? "Saving…" : "Save"}
                    </Button>
                    <Button
                      type="button"
                      variant="ghost"
                      onClick={cancelEdit}
                      disabled={savingEdit}
                      className="text-xs px-3 py-1.5"
                    >
                      Cancel
                    </Button>
                    <Button
                      type="button"
                      variant="danger"
                      onClick={() => handleDelete(p)}
                      disabled={savingEdit}
                      className="text-xs px-3 py-1.5"
                    >
                      <Trash2 size={14} className="mr-1" /> Delete
                    </Button>
                  </div>
                </div>
              ) : (
                /* ---- View mode ---- */
                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-medium text-foreground">{p.name}</p>
                    <p className="text-xs text-muted-foreground">
                      {p.priority} · first response {p.first_response_minutes}m · resolve in {p.resolution_hours}h
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <span
                      className={`rounded-full px-2.5 py-1 text-xs font-medium ${
                        p.is_active
                          ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300"
                          : "bg-muted text-muted-foreground"
                      }`}
                    >
                      {p.is_active ? "Active" : "Inactive"}
                    </span>
                    {canManage && (
                      <>
                        <Button
                          type="button"
                          variant="ghost"
                          onClick={() => startEdit(p)}
                          className="text-xs px-3 py-1.5"
                        >
                          <Pencil size={14} className="mr-1" /> Edit
                        </Button>
                        <Button
                          type="button"
                          variant="danger"
                          onClick={() => handleDeactivate(p)}
                          disabled={deactivatingId === p.id}
                          className="text-xs px-3 py-1.5"
                        >
                          {deactivatingId === p.id ? "…" : <><Trash2 size={14} className="mr-1" /> Deactivate</>}
                        </Button>
                      </>
                    )}
                  </div>
                </div>
              )}
            </div>
          ))}
          {policies.length === 0 && <EmptyState>No policies yet.</EmptyState>}
        </ListPanel>
      )}

      {canManage && (
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
