"use client";

import { useEffect, useState, useCallback } from "react";
import RequireAuth from "../components/RequireAuth";
import PageHeader from "../components/ui/PageHeader";
import PageTransition from "../components/ui/PageTransition";
import Spinner from "../components/ui/Spinner";
import { ListPanel } from "../components/ui/Card";
import { api } from "../../lib/api";
import { hasPermission } from "../../lib/permissions";
import { useAuth } from "../../lib/auth-context";

function CustomersPage() {
  const { user } = useAuth();
  const [orgs, setOrgs] = useState([]);
  const [contacts, setContacts] = useState([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    if (!hasPermission(user, "organization.manage")) {
      setLoading(false);
      return;
    }
    try {
      const [o, c] = await Promise.all([api.listOrganizations(), api.listContacts()]);
      setOrgs(o);
      setContacts(c);
    } finally {
      setLoading(false);
    }
  }, [user]);

  useEffect(() => {
    load();
  }, [load]);

  if (!hasPermission(user, "organization.manage")) {
    return (
      <PageTransition className="mx-auto max-w-3xl px-4 py-10">
        <p className="text-sm text-danger">You don&apos;t have access to this page.</p>
      </PageTransition>
    );
  }

  return (
    <PageTransition className="mx-auto max-w-4xl px-4 py-8">
      <PageHeader title="Customers" description="Organizations and contacts." />
      {loading ? (
        <Spinner />
      ) : (
        <div className="grid gap-6 md:grid-cols-2">
          <ListPanel>
            <p className="border-b border-border px-4 py-2 text-xs font-medium uppercase text-muted-foreground">
              Organizations
            </p>
            {orgs.map((o) => (
              <div key={o.id} className="px-4 py-3 text-sm">
                <p className="font-medium">{o.name}</p>
                <p className="text-xs text-muted-foreground">{o.org_type}</p>
              </div>
            ))}
          </ListPanel>
          <ListPanel>
            <p className="border-b border-border px-4 py-2 text-xs font-medium uppercase text-muted-foreground">
              Contacts
            </p>
            {contacts.map((c) => (
              <div key={c.id} className="px-4 py-3 text-sm">
                <p className="font-medium">{c.full_name}</p>
                <p className="text-xs text-muted-foreground">{c.email}</p>
              </div>
            ))}
          </ListPanel>
        </div>
      )}
    </PageTransition>
  );
}

export default function Page() {
  return (
    <RequireAuth>
      <CustomersPage />
    </RequireAuth>
  );
}
