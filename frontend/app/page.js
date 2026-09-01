"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "../lib/auth-context";
import { homeForUser } from "../lib/permissions";
import Spinner from "./components/ui/Spinner";
import PageTransition from "./components/ui/PageTransition";

export default function Home() {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (loading) return;
    router.replace(homeForUser(user));
  }, [user, loading, router]);

  return (
    <PageTransition className="mx-auto max-w-5xl px-4 py-10">
      <Spinner />
    </PageTransition>
  );
}
