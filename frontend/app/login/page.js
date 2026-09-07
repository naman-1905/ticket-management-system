"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { useAuth } from "../../lib/auth-context";
import { homeForUser } from "../../lib/permissions";
import { api, setTokens } from "../../lib/api";
import AuthLayout from "../components/ui/AuthLayout";
import Button from "../components/ui/Button";
import Input from "../components/ui/Input";

const fieldVariants = {
  hidden: { opacity: 0, y: 8 },
  visible: (i) => ({
    opacity: 1,
    y: 0,
    transition: { delay: i * 0.08, duration: 0.3 },
  }),
};

export default function LoginPage() {
  const { login } = useAuth();
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      const me = await login(email, password);
      // Return to the page the user was on before the session-expiry redirect.
      const next = new URLSearchParams(window.location.search).get("next");
      if (next && next.startsWith("/") && !next.startsWith("//")) {
        router.push(next);
      } else {
        router.push(homeForUser(me));
      }
    } catch (err) {
      setError(err.message || "Login failed");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleGoogleLogin() {
    try {
      const data = await api.googleAuthLogin();
      window.location.href = data.url;
    } catch (err) {
      setError(err.message || "Google login not available");
    }
  }

  return (
    <AuthLayout
      title="Welcome back"
      subtitle="Log in to manage your tickets."
      footer={
        <p className="text-sm text-muted-foreground">
          No account?{" "}
          <Link href="/register" className="font-medium text-accent hover:text-accent-hover transition-colors">
            Register
          </Link>
        </p>
      }
    >
      <form onSubmit={handleSubmit} className="space-y-4">
        <motion.div custom={0} initial="hidden" animate="visible" variants={fieldVariants}>
          <Input
            label="Email"
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
        </motion.div>
        <motion.div custom={1} initial="hidden" animate="visible" variants={fieldVariants}>
          <Input
            label="Password"
            type="password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </motion.div>

        {error && (
          <motion.p initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="text-sm text-danger">
            {error}
          </motion.p>
        )}

        <motion.div custom={2} initial="hidden" animate="visible" variants={fieldVariants}>
          <Button type="submit" disabled={submitting} className="w-full">
            {submitting ? "Logging in…" : "Log in"}
          </Button>
        </motion.div>

        <motion.div custom={3} initial="hidden" animate="visible" variants={fieldVariants}>
          <div className="relative my-4">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-border" />
            </div>
            <div className="relative flex justify-center text-xs uppercase">
              <span className="bg-surface px-3 text-muted-foreground dark:bg-background">Or continue with</span>
            </div>
          </div>
          <Button type="button" variant="outline" onClick={handleGoogleLogin} className="w-full gap-2">
            <svg className="h-4 w-4" viewBox="0 0 24 24">
              <path
                d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                fill="#4285F4"
              />
              <path
                d="M12 23c2.97 0 5.46-.98 7.28-2.66l-2.77-2.77c-.8.53-1.77.84-2.91.84-2.26 0-4.18-1.54-4.91-3.64H2.81v2.84C4.6 20.69 8.03 23 12 23z"
                fill="#34A853"
              />
              <path
                d="M7.09 14.77c-.22-.66-.35-1.36-.35-2.07s.13-1.41.35-2.07V7.78H2.81C1.94 9.23 1.44 10.98 1.44 12.7c0 1.72.5 3.47 1.37 4.92l4.28-2.85z"
                fill="#FBBC05"
              />
              <path
                d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.81 7.78l4.28 2.84c.73-2.1 2.65-3.64 4.91-3.64z"
                fill="#EA4335"
              />
            </svg>
            Sign in with Google
          </Button>
        </motion.div>
      </form>
    </AuthLayout>
  );
}
