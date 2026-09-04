"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { useAuth } from "../../lib/auth-context";
import { hasPermission } from "../../lib/permissions";
import Spinner from "./ui/Spinner";
import PageTransition from "./ui/PageTransition";

export default function RequireAuth({ children, roles, permissions }) {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (loading) return;
    if (!user) {
      const next = typeof window !== "undefined" ? window.location.pathname + window.location.search : "";
      router.replace(next ? `/login?next=${encodeURIComponent(next)}` : "/login");
    }
  }, [user, loading, router]);

  if (loading) {
    return (
      <PageTransition className="mx-auto max-w-5xl px-4 py-10">
        <Spinner />
      </PageTransition>
    );
  }

  if (!user) return null;

  if (roles && !roles.includes(user.role)) {
    return (
      <PageTransition className="mx-auto max-w-5xl px-4 py-10">
        <p className="text-sm text-danger">You don&apos;t have access to this page.</p>
      </PageTransition>
    );
  }

  if (permissions && !permissions.some((p) => hasPermission(user, p))) {
    return (
      <PageTransition className="mx-auto max-w-5xl px-4 py-10">
        <p className="text-sm text-danger">You don&apos;t have access to this page.</p>
      </PageTransition>
    );
  }

  return children;
}
