"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { useAuth } from "../../lib/auth-context";
import Spinner from "./ui/Spinner";
import PageTransition from "./ui/PageTransition";

export default function RequireAuth({ children, roles }) {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (loading) return;
    if (!user) router.replace("/login");
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

  return children;
}
