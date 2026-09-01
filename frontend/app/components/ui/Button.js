"use client";

import { motion } from "framer-motion";

const variants = {
  primary:
    "bg-accent text-accent-foreground hover:bg-accent-hover focus-visible:ring-accent/40",
  secondary:
    "border border-border bg-surface text-foreground hover:bg-muted focus-visible:ring-accent/30",
  ghost: "text-muted-foreground hover:text-foreground hover:bg-muted focus-visible:ring-accent/30",
  danger: "text-muted-foreground hover:text-danger focus-visible:ring-danger/30",
};

export default function Button({
  children,
  variant = "primary",
  className = "",
  disabled,
  type = "button",
  as: Component = motion.button,
  ...props
}) {
  return (
    <Component
      type={Component === motion.button ? type : undefined}
      disabled={disabled}
      whileHover={disabled ? undefined : { scale: 1.02 }}
      whileTap={disabled ? undefined : { scale: 0.98 }}
      className={`inline-flex items-center justify-center rounded-full px-4 py-2 text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 disabled:opacity-50 disabled:pointer-events-none ${variants[variant]} ${className}`}
      {...props}
    >
      {children}
    </Component>
  );
}
