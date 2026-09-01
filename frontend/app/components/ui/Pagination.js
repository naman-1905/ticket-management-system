"use client";

import { motion } from "framer-motion";
import Button from "./Button";

export default function Pagination({ page, totalPages, onPageChange }) {
  if (totalPages <= 1) return null;

  return (
    <div className="mt-6 flex items-center justify-center gap-3 text-sm">
      <Button
        variant="secondary"
        disabled={page <= 1}
        onClick={() => onPageChange(page - 1)}
        className="px-3 py-1.5"
      >
        Previous
      </Button>
      <span className="text-muted-foreground">
        Page {page} of {totalPages}
      </span>
      <Button
        variant="secondary"
        disabled={page >= totalPages}
        onClick={() => onPageChange(page + 1)}
        className="px-3 py-1.5"
      >
        Next
      </Button>
    </div>
  );
}

export function AnimatedListRow({ children, className = "", as: Component = motion.div, ...props }) {
  return (
    <Component
      whileHover={{ backgroundColor: "var(--muted)" }}
      transition={{ duration: 0.15 }}
      className={`px-4 py-3 ${className}`}
      {...props}
    >
      {children}
    </Component>
  );
}
