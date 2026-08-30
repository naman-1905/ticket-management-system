"use client";

import { useEffect, useState, useCallback } from "react";
import RequireAuth from "../components/RequireAuth";
import { useAuth } from "../../lib/auth-context";
import { api } from "../../lib/api";

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
    <div className="max-w-3xl mx-auto px-4 py-8">
      <h1 className="text-2xl font-semibold mb-6">SLA Policies</h1>

      {error && <p className="text-sm text-red-600 mb-4">{error}</p>}

      {loading ? (
        <p className="text-slate-500 text-sm">Loading…</p>
      ) : (
        <div className="bg-white border border-slate-200 rounded-lg divide-y divide-slate-100 mb-8">
          {policies.map((p) => (
            <div key={p.id} className="px-4 py-3 flex items-center justify-between text-sm">
              <div>
                <p className="font-medium">{p.name}</p>
                <p className="text-slate-500 text-xs">
                  {p.priority} · first response {p.first_response_minutes}m · resolve in {p.resolution_hours}h
                </p>
              </div>
              <span
                className={`text-xs px-2 py-1 rounded-full ${
                  p.is_active ? "bg-emerald-100 text-emerald-700" : "bg-slate-100 text-slate-500"
                }`}
              >
                {p.is_active ? "Active" : "Inactive"}
              </span>
            </div>
          ))}
          {policies.length === 0 && <p className="px-4 py-3 text-sm text-slate-500">No policies yet.</p>}
        </div>
      )}

      {user.role === "ADMIN" && (
        <form onSubmit={handleCreate} className="bg-white border border-slate-200 rounded-lg p-4 space-y-3">
          <h2 className="font-medium text-sm">Create policy</h2>
          <input
            required
            placeholder="Name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="w-full border border-slate-300 rounded-md px-3 py-2 text-sm"
          />
          <div className="flex gap-3">
            <select
              value={priority}
              onChange={(e) => setPriority(e.target.value)}
              className="border border-slate-300 rounded-md px-3 py-2 text-sm bg-white"
            >
              {["P1", "P2", "P3", "P4"].map((p) => (
                <option key={p} value={p}>
                  {p}
                </option>
              ))}
            </select>
            <input
              type="number"
              min={1}
              value={firstResponse}
              onChange={(e) => setFirstResponse(e.target.value)}
              placeholder="First response (min)"
              className="border border-slate-300 rounded-md px-3 py-2 text-sm w-40"
            />
            <input
              type="number"
              min={1}
              value={resolutionHours}
              onChange={(e) => setResolutionHours(e.target.value)}
              placeholder="Resolution (hrs)"
              className="border border-slate-300 rounded-md px-3 py-2 text-sm w-40"
            />
          </div>
          <button
            type="submit"
            disabled={submitting}
            className="bg-slate-900 text-white rounded-md px-4 py-2 text-sm font-medium hover:bg-slate-800 disabled:opacity-50"
          >
            {submitting ? "Creating…" : "Create policy"}
          </button>
        </form>
      )}
    </div>
  );
}

export default function Page() {
  return (
    <RequireAuth roles={["AGENT", "ADMIN"]}>
      <SlaPage />
    </RequireAuth>
  );
}
