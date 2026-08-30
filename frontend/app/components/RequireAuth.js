"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "../../lib/auth-context";

export default function RequireAuth({ roles, children }) {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !user) router.replace("/login");
  }, [loading, user, router]);

  if (loading || !user) {
    return <div className="max-w-5xl mx-auto px-4 py-10 text-slate-500 text-sm">Loading…</div>;
  }

  if (roles && !roles.includes(user.role)) {
    return <div className="max-w-5xl mx-auto px-4 py-10 text-red-600 text-sm">You don&apos;t have access to this page.</div>;
  }

  return children;
}
