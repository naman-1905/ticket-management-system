"use client";

import { useEffect, useState, useCallback } from "react";
import RequireAuth from "../../components/RequireAuth";
import { api } from "../../../lib/api";
import EmptyState from "../../components/ui/EmptyState";
import PageHeader from "../../components/ui/PageHeader";
import PageTransition from "../../components/ui/PageTransition";
import Select from "../../components/ui/Select";
import Spinner from "../../components/ui/Spinner";
import { ListPanel } from "../../components/ui/Card";

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
    <PageTransition className="mx-auto max-w-3xl px-4 py-8">
      <PageHeader title="Users" description="Manage roles and access for team members." />
      {error && <p className="mb-4 text-sm text-danger">{error}</p>}
      {loading ? (
        <Spinner label="Loading users…" />
      ) : (
        <ListPanel>
          {users.map((u) => (
            <div key={u.id} className="flex items-center justify-between px-4 py-3 text-sm">
              <div>
                <p className="font-medium text-foreground">{u.full_name}</p>
                <p className="text-xs text-muted-foreground">{u.email}</p>
              </div>
              <Select
                value={u.role}
                disabled={updatingId === u.id}
                onChange={(e) => handleRoleChange(u.id, e.target.value)}
                className="rounded-full px-3 py-1.5"
              >
                {["CUSTOMER", "CUSTOMER_ADMIN", "AGENT", "SUPERVISOR", "ADMIN", "OWNER"].map((r) => (
                  <option key={r} value={r}>
                    {r}
                  </option>
                ))}
              </Select>
            </div>
          ))}
          {users.length === 0 && <EmptyState>No users found.</EmptyState>}
        </ListPanel>
      )}
    </PageTransition>
  );
}

export default function Page() {
  return (
    <RequireAuth permissions={["user.manage"]}>
      <UsersPage />
    </RequireAuth>
  );
}
