"use client";

import { motion } from "framer-motion";
import BrandMark from "./BrandMark";
import ThemeToggle from "./ThemeToggle";
import { Card } from "./Card";

export default function AuthLayout({ title, subtitle, children, footer }) {
  return (
    <div className="relative min-h-[calc(100vh-0px)] flex items-center justify-center px-4 py-12">
      <div className="pointer-events-none absolute inset-0 overflow-hidden">
        <div className="absolute -top-24 left-1/2 h-72 w-72 -translate-x-1/2 rounded-full bg-accent/10 blur-3xl dark:bg-accent/5" />
        <div className="absolute bottom-0 right-0 h-64 w-64 rounded-full bg-accent/5 blur-3xl dark:bg-accent/10" />
      </div>

      <ThemeToggle className="absolute right-4 top-4 z-10" />

      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, ease: "easeOut" }}
        className="relative w-full max-w-sm"
      >
        <div className="mb-8 text-center">
          <BrandMark size="lg" />
          <h1 className="mt-4 text-2xl font-semibold tracking-tight text-foreground">{title}</h1>
          {subtitle && <p className="mt-1 text-sm text-muted-foreground">{subtitle}</p>}
        </div>

        <Card className="shadow-sm">{children}</Card>

        {footer && <div className="mt-4 text-center">{footer}</div>}
      </motion.div>
    </div>
  );
}
