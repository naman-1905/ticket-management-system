"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import RequireAuth from "../../components/RequireAuth";
import Button from "../../components/ui/Button";
import Input from "../../components/ui/Input";
import PageHeader from "../../components/ui/PageHeader";
import PageTransition from "../../components/ui/PageTransition";
import Select from "../../components/ui/Select";
import Textarea from "../../components/ui/Textarea";
import { Card } from "../../components/ui/Card";
import { api } from "../../../lib/api";

const fieldVariants = {
  hidden: { opacity: 0, y: 8 },
  visible: (i) => ({
    opacity: 1,
    y: 0,
    transition: { delay: i * 0.06, duration: 0.3 },
  }),
};

function NewTicketForm() {
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
      const ticket = await api.createTicket({
        title,
        description,
        priority,
        category: category || undefined,
      });
      router.push(`/tickets/${ticket.id}`);
    } catch (err) {
      setError(err.message || "Failed to create ticket");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <PageTransition className="mx-auto max-w-xl px-4 py-8">
      <PageHeader title="New ticket" description="Describe the issue and set a priority." />

      <Card>
        <form onSubmit={handleSubmit} className="space-y-4">
          <motion.div custom={0} initial="hidden" animate="visible" variants={fieldVariants}>
            <Input
              label="Title"
              required
              maxLength={300}
              value={title}
              onChange={(e) => setTitle(e.target.value)}
            />
          </motion.div>
          <motion.div custom={1} initial="hidden" animate="visible" variants={fieldVariants}>
            <Textarea
              label="Description"
              required
              rows={5}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
            />
          </motion.div>
          <motion.div custom={2} initial="hidden" animate="visible" variants={fieldVariants} className="flex gap-4">
            <Select
              label="Priority"
              value={priority}
              onChange={(e) => setPriority(e.target.value)}
              className="flex-1"
            >
              <option value="P1">P1 — Critical</option>
              <option value="P2">P2 — High</option>
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
          </motion.div>

          {error && <p className="text-sm text-danger">{error}</p>}

          <motion.div custom={3} initial="hidden" animate="visible" variants={fieldVariants}>
            <Button type="submit" disabled={submitting}>
              {submitting ? "Creating…" : "Create ticket"}
            </Button>
          </motion.div>
        </form>
      </Card>
    </PageTransition>
  );
}

export default function Page() {
  return (
    <RequireAuth>
      <NewTicketForm />
    </RequireAuth>
  );
}
