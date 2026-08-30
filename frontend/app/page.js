"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "../lib/auth-context";

export default function Home() {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (loading) return;
    router.replace(user ? "/tickets" : "/login");
  }, [user, loading, router]);

  return <div className="max-w-5xl mx-auto px-4 py-10 text-slate-500 text-sm">Loading…</div>;
}
