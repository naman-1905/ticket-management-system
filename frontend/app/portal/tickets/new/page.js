"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import RequireAuth from "../../../components/RequireAuth";
import Button from "../../../components/ui/Button";
import Input from "../../../components/ui/Input";
import PageHeader from "../../../components/ui/PageHeader";
import PageTransition from "../../../components/ui/PageTransition";
import Select from "../../../components/ui/Select";
import Textarea from "../../../components/ui/Textarea";
import { Card } from "../../../components/ui/Card";
import { api } from "../../../../lib/api";

function PortalNewTicket() {
  const router = useRouter();
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [priority, setPriority] = useState("P3");
  const [category, setCategory] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      const idempotencyKey =
        typeof crypto !== "undefined" && crypto.randomUUID ? crypto.randomUUID() : undefined;
      const ticket = await api.createTicket(
        { title, description, priority, category: category || undefined },
        idempotencyKey
      );
      router.push("/portal/tickets");
    } catch (err) {
      setError(err.message || "Failed to create ticket");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <PageTransition className="mx-auto max-w-xl px-4 py-8">
      <PageHeader title="New ticket" description="Tell us what's going on and we'll get back to you." />
      <Card>
        <form onSubmit={handleSubmit} className="space-y-4">
          <Input
            label="Title"
            required
            maxLength={300}
            value={title}
            onChange={(e) => setTitle(e.target.value)}
          />
          <Textarea
            label="Description"
            required
            rows={5}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
          <div className="flex gap-4">
            <Select
              label="Priority"
              value={priority}
              onChange={(e) => setPriority(e.target.value)}
              className="flex-1"
            >
              <option value="P3">P3 — Normal</option>
              <option value="P4">P4 — Low</option>
            </Select>
            <Input
              label="Category (optional)"
              maxLength={50}
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              className="flex-1"
            />
          </div>

          {error && <p className="text-sm text-danger">{error}</p>}

          <Button type="submit" disabled={submitting}>
            {submitting ? "Creating…" : "Submit ticket"}
          </Button>
        </form>
      </Card>
    </PageTransition>
  );
}

export default function Page() {
  return (
    <RequireAuth>
      <PortalNewTicket />
    </RequireAuth>
  );
}
