"use client";

import { useEffect, useState, useCallback } from "react";
import RequireAuth from "../../components/RequireAuth";
import { api } from "../../../lib/api";

function UsersPage() {
  const [users, setUsers] = useState([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [updatingId, setUpdatingId] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setUsers(await api.listUsers());
    } catch (err) {
      setError(err.message || "Failed to load users");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function handleRoleChange(userId, role) {
    setUpdatingId(userId);
    setError("");
    try {
      await api.updateUserRole(userId, role);
      await load();
    } catch (err) {
      setError(err.message || "Failed to update role");
    } finally {
      setUpdatingId(null);
    }
  }

  return (
    <div className="max-w-3xl mx-auto px-4 py-8">
      <h1 className="text-2xl font-semibold mb-6">Users</h1>
      {error && <p className="text-sm text-red-600 mb-4">{error}</p>}
      {loading ? (
        <p className="text-slate-500 text-sm">Loading…</p>
      ) : (
        <div className="bg-white border border-slate-200 rounded-lg divide-y divide-slate-100">
          {users.map((u) => (
            <div key={u.id} className="px-4 py-3 flex items-center justify-between text-sm">
              <div>
                <p className="font-medium">{u.full_name}</p>
                <p className="text-slate-500 text-xs">{u.email}</p>
              </div>
              <select
                value={u.role}
                disabled={updatingId === u.id}
                onChange={(e) => handleRoleChange(u.id, e.target.value)}
                className="border border-slate-300 rounded-md px-2 py-1 text-sm bg-white"
              >
                {["CUSTOMER", "AGENT", "ADMIN"].map((r) => (
                  <option key={r} value={r}>
                    {r}
                  </option>
                ))}
              </select>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default function Page() {
  return (
    <RequireAuth roles={["ADMIN"]}>
      <UsersPage />
    </RequireAuth>
  );
}
