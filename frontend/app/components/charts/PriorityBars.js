"use client";

import { motion } from "framer-motion";
import { PRIORITY_COLORS } from "./palette";

const ORDER = ["P1", "P2", "P3", "P4"];

export default function PriorityBars({ data }) {
  const items = ORDER.map((p) => ({ p, count: (data.find((d) => d.priority === p)?.count) || 0 }));
  const max = Math.max(1, ...items.map((i) => i.count));

  return (
    <div className="space-y-3">
      {items.map((it, idx) => (
        <div key={it.p} className="flex items-center gap-3">
          <span className="w-8 text-sm font-semibold tabular-nums text-foreground">{it.p}</span>
          <div className="h-2.5 flex-1 overflow-hidden rounded-full bg-muted">
            <motion.div
              className="h-full rounded-full"
              style={{ background: PRIORITY_COLORS[it.p] }}
              initial={{ width: 0 }}
              animate={{ width: `${(it.count / max) * 100}%` }}
              transition={{ duration: 0.7, delay: 0.05 * idx, ease: "easeOut" }}
            />
          </div>
          <span className="w-8 text-right text-sm font-semibold tabular-nums text-foreground">{it.count}</span>
        </div>
      ))}
    </div>
  );
}
