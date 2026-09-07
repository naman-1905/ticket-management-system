"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { api, setTokens } from "../../../lib/api";
import { useAuth } from "../../../lib/auth-context";
import { homeForUser } from "../../../lib/permissions";
import Spinner from "../../components/ui/Spinner";

export default function GoogleCallbackPage() {
  const router = useRouter();
  const { setUser } = useAuth();
  const [error, setError] = useState("");

  useEffect(() => {
    async function handleCallback() {
      const params = new URLSearchParams(window.location.search);
      const code = params.get("code");
      if (!code) {
        setError("Missing authorization code");
        return;
      }
      try {
        const tokens = await api.googleAuthCallback(code);
        setTokens(tokens);
        const me = await api.me();
        setUser(me);
        router.replace(homeForUser(me));
      } catch (err) {
        setError(err.message || "Google login failed");
      }
    }
    handleCallback();
  }, [router, setUser]);

  return (
    <div className="flex min-h-[60vh] items-center justify-center">
      {error ? (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="text-center">
          <p className="mb-4 text-danger">{error}</p>
          <button onClick={() => router.push("/login")} className="text-sm text-accent hover:underline">
            Back to login
          </button>
        </motion.div>
      ) : (
        <div className="flex flex-col items-center gap-3">
          <Spinner />
          <p className="text-sm text-muted-foreground">Signing in with Google…</p>
        </div>
      )}
    </div>
  );
}