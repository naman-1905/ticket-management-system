"use client";

import { motion } from "framer-motion";

export default function Spinner({ label = "Loading…" }) {
  return (
    <div className="flex items-center gap-3 text-sm text-muted-foreground">
      <motion.span
        className="inline-block h-4 w-4 rounded-full border-2 border-border border-t-accent"
        animate={{ rotate: 360 }}
        transition={{ duration: 0.8, repeat: Infinity, ease: "linear" }}
      />
      {label}
    </div>
  );
}
