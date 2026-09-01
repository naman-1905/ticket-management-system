"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { useAuth } from "../../lib/auth-context";
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
      await login(email, password);
      router.push("/tickets");
    } catch (err) {
      setError(err.message || "Login failed");
    } finally {
      setSubmitting(false);
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
      </form>
    </AuthLayout>
  );
}
