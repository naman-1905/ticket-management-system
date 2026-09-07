"use client";

import { useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { useAuth } from "../lib/auth-context";
import { homeForUser } from "../lib/permissions";
import Spinner from "./components/ui/Spinner";
import PageTransition from "./components/ui/PageTransition";
import Button from "./components/ui/Button";

const features = [
  {
    title: "Ticket Management",
    description: "Create, assign, and track support tickets with full lifecycle management.",
  },
  {
    title: "SLA Tracking",
    description: "Monitor first response and resolution times against your SLA policies.",
  },
  {
    title: "Email Automation",
    description: "Automatically convert incoming emails into structured tickets using AI.",
  },
  {
    title: "Team Collaboration",
    description: "Internal notes, team assignments, and role-based access control.",
  },
  {
    title: "Reporting & Analytics",
    description: "Dashboards with trends, SLA breach tracking, and resolution metrics.",
  },
  {
    title: "Knowledge Base",
    description: "Share articles and help documents with your customers.",
  },
];

export default function Home() {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (loading) return;
    if (user) {
      router.replace(homeForUser(user));
    }
  }, [user, loading, router]);

  if (loading || user) {
    return (
      <PageTransition className="mx-auto max-w-5xl px-4 py-10">
        <Spinner />
      </PageTransition>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      {/* Hero */}
      <section className="flex flex-col items-center justify-center px-4 py-24 text-center">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="mx-auto max-w-3xl"
        >
          <h1 className="mb-6 text-4xl font-bold tracking-tight text-foreground sm:text-5xl">
            Modern Service Desk for Your Team
          </h1>
          <p className="mb-8 text-lg text-muted-foreground">
            Manage support tickets, track SLAs, and automate email-to-ticket workflows — all in one
            place.
          </p>
          <div className="flex flex-wrap items-center justify-center gap-3">
            <Link href="/login">
              <Button size="lg" className="gap-2">
                Get Started
              </Button>
            </Link>
            <Link href="/register">
              <Button variant="outline" size="lg">
                Create Account
              </Button>
            </Link>
          </div>
        </motion.div>
      </section>

      {/* Features */}
      <section className="mx-auto max-w-5xl px-4 py-16">
        <h2 className="mb-8 text-center text-2xl font-semibold text-foreground">
          Everything you need to support your customers
        </h2>
        <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {features.map((f, i) => (
            <motion.div
              key={f.title}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.08, duration: 0.3 }}
              className="rounded-2xl border border-border bg-surface p-5 dark:bg-background"
            >
              <h3 className="mb-2 font-medium text-foreground">{f.title}</h3>
              <p className="text-sm text-muted-foreground">{f.description}</p>
            </motion.div>
          ))}
        </div>
      </section>

      {/* CTA */}
      <section className="px-4 py-16 text-center">
        <h2 className="mb-4 text-2xl font-semibold text-foreground">Ready to get started?</h2>
        <p className="mb-6 text-muted-foreground">
          Join your team and start managing tickets in minutes.
        </p>
        <Link href="/register">
          <Button size="lg">Sign Up Free</Button>
        </Link>
      </section>
    </div>
  );
}
