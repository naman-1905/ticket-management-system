"use client";

import { useId } from "react";
import { motion } from "framer-motion";

/**
 * Segmented control for switching between a small set of options.
 *
 * @param {Array<{ key: string, label: string, icon?: React.ComponentType, color?: string }>} options
 *        Each option may specify an optional `color`; when the tab is active its icon
 *        is rendered in that color so the active section reads at a glance.
 * @param {string} value        active option key
 * @param {(key: string) => void} onChange
 */
export default function Tabs({ options, value, onChange, className = "" }) {
  const uid = useId().replace(/:/g, "");
  return (
    <div role="tablist" className={`inline-flex items-center gap-1 rounded-full border border-border bg-muted p-1 ${className}`}>
      {options.map((opt) => {
        const active = opt.key === value;
        const Icon = opt.icon;
        return (
          <button
            key={opt.key}
            type="button"
            role="tab"
            aria-selected={active}
            onClick={() => onChange(opt.key)}
            className={`relative inline-flex items-center gap-1.5 rounded-full px-3.5 py-1.5 text-sm font-medium transition-colors ${
              active ? "text-foreground" : "text-muted-foreground hover:text-foreground"
            }`}
          >
            {active && (
              <motion.span
                layoutId={`tabs-pill-${uid}`}
                className="absolute inset-0 rounded-full bg-surface shadow-sm ring-1 ring-border"
                transition={{ type: "spring", stiffness: 420, damping: 34 }}
              />
            )}
            {Icon && (
              <Icon
                size={15}
                strokeWidth={2}
                className="shrink-0"
                style={active && opt.color ? { color: opt.color } : undefined}
              />
            )}
            <span className="relative z-10">{opt.label}</span>
          </button>
        );
      })}
    </div>
  );
}
