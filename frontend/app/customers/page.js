"use client";

import { useEffect, useState, useCallback } from "react";
import RequireAuth from "../components/RequireAuth";
import PageHeader from "../components/ui/PageHeader";
import PageTransition from "../components/ui/PageTransition";
import Spinner from "../components/ui/Spinner";
import { Card, ListPanel } from "../components/ui/Card";
import Input from "../components/ui/Input";
import Select from "../components/ui/Select";
import Button from "../components/ui/Button";
import { api } from "../../lib/api";
import { hasPermission } from "../../lib/permissions";
import { useAuth } from "../../lib/auth-context";

function CustomersPage() {
  const { user } = useAuth();
  const [orgs, setOrgs] = useState([]);
  const [contacts, setContacts] = useState([]);
  const [loading, setLoading] = useState(true);

  const [orgName, setOrgName] = useState("");
  const [orgType, setOrgType] = useState("customer");
  const [orgError, setOrgError] = useState("");
  const [contactEmail, setContactEmail] = useState("");
  const [contactName, setContactName] = useState("");
  const [contactOrgId, setContactOrgId] = useState("");
  const [contactError, setContactError] = useState("");

  const load = useCallback(async () => {
    if (!hasPermission(user, "organization.manage") && !hasPermission(user, "contact.manage")) {
      setLoading(false);
      return;
    }
    setLoading(true);
    const tasks = [];
    if (hasPermission(user, "organization.manage")) {
      tasks.push(api.listOrganizations().then(setOrgs).catch(() => {}));
    }
    if (hasPermission(user, "contact.manage")) {
      tasks.push(api.listContacts().then(setContacts).catch(() => {}));
    }
    await Promise.all(tasks);
    setLoading(false);
  }, [user]);

  useEffect(() => {
    load();
  }, [load]);

  async function handleCreateOrg(e) {
    e.preventDefault();
    setOrgError("");
    try {
      await api.createOrganization({ name: orgName, org_type: orgType });
      setOrgName("");
      await load();
    } catch (err) {
      setOrgError(err.message || "Failed to create organization");
    }
  }

  async function handleCreateContact(e) {
    e.preventDefault();
    setContactError("");
    try {
      await api.createContact({
        email: contactEmail,
        full_name: contactName,
        organization_id: contactOrgId || undefined,
      });
      setContactEmail("");
      setContactName("");
      setContactOrgId("");
      await load();
    } catch (err) {
      setContactError(err.message || "Failed to create contact");
    }
  }

  if (!hasPermission(user, "organization.manage") && !hasPermission(user, "contact.manage")) {
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
        <>
        <div className="mb-6 grid gap-6 md:grid-cols-2">
          {hasPermission(user, "organization.manage") && (
            <Card>
              <h2 className="mb-3 text-sm font-semibold text-foreground">New organization</h2>
              <form onSubmit={handleCreateOrg} className="space-y-3">
                <Input label="Name" required maxLength={200} value={orgName} onChange={(e) => setOrgName(e.target.value)} />
                <Select label="Type" value={orgType} onChange={(e) => setOrgType(e.target.value)}>
                  <option value="customer">Customer</option>
                  <option value="partner">Partner</option>
                  <option value="internal">Internal</option>
                </Select>
                {orgError && <p className="text-sm text-danger">{orgError}</p>}
                <Button type="submit">Add organization</Button>
              </form>
            </Card>
          )}
          {hasPermission(user, "contact.manage") && (
            <Card>
              <h2 className="mb-3 text-sm font-semibold text-foreground">New contact</h2>
              <form onSubmit={handleCreateContact} className="space-y-3">
                <Input label="Full name" required maxLength={200} value={contactName} onChange={(e) => setContactName(e.target.value)} />
                <Input label="Email" type="email" required value={contactEmail} onChange={(e) => setContactEmail(e.target.value)} />
                <Select label="Organization (optional)" value={contactOrgId} onChange={(e) => setContactOrgId(e.target.value)}>
                  <option value="">None</option>
                  {orgs.map((o) => (
                    <option key={o.id} value={o.id}>{o.name}</option>
                  ))}
                </Select>
                {contactError && <p className="text-sm text-danger">{contactError}</p>}
                <Button type="submit">Add contact</Button>
              </form>
            </Card>
          )}
        </div>
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
        </>
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
