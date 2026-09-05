"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { formatStatus } from "../../../lib/format";

export default function DonutChart({ data, size = 180 }) {
  const [active, setActive] = useState(null);
  const total = data.reduce((s, d) => s + d.value, 0);
  const R = size / 2;
  const r = R - 16;
  const C = 2 * Math.PI * r;
  const cx = R;
  const cy = R;

  let offset = 0;
  const segments = data.map((d) => {
    const len = total > 0 ? (d.value / total) * C : 0;
    const seg = { ...d, len, offset };
    offset += len;
    return seg;
  });

  const activeData = active != null ? data[active] : null;
  const pct = activeData && total > 0 ? Math.round((activeData.value / total) * 100) : 0;

  if (total === 0) {
    return <p className="py-10 text-center text-sm text-muted-foreground">No tickets yet</p>;
  }

  return (
    <div className="flex flex-col items-center gap-5 sm:flex-row">
      <div className="relative shrink-0" style={{ width: size, height: size }}>
        <motion.svg
          width={size}
          height={size}
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.5, ease: "easeOut" }}
          style={{ transformBox: "fill-box", transformOrigin: "center" }}
        >
          <g transform={`rotate(-90 ${cx} ${cy})`}>
            {segments.map((seg, i) => (
              <circle
                key={i}
                cx={cx}
                cy={cy}
                r={r}
                fill="none"
                stroke={seg.color}
                strokeWidth={active === i ? 20 : 14}
                strokeDasharray={`${seg.len} ${C - seg.len}`}
                strokeDashoffset={-seg.offset}
                opacity={active == null || active === i ? 1 : 0.35}
                style={{ transition: "stroke-width .18s ease, opacity .18s ease", cursor: "pointer" }}
                onMouseEnter={() => setActive(i)}
                onMouseLeave={() => setActive(null)}
              />
            ))}
          </g>
        </motion.svg>
        <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-3xl font-semibold tabular-nums text-foreground">
            {activeData ? activeData.value : total}
          </span>
          <span className="mt-0.5 text-xs text-muted-foreground">{activeData ? `${pct}%` : "Total"}</span>
        </div>
      </div>

      <ul className="w-full flex-1 space-y-2">
        {data.map((d, i) => (
          <li
            key={i}
            onMouseEnter={() => setActive(i)}
            onMouseLeave={() => setActive(null)}
            className="flex cursor-pointer items-center gap-2 text-sm transition-opacity"
            style={{ opacity: active == null || active === i ? 1 : 0.5 }}
          >
            <span className="inline-block h-2.5 w-2.5 shrink-0 rounded-full" style={{ background: d.color }} />
            <span className="truncate text-muted-foreground">{formatStatus(d.label)}</span>
            <span className="ml-auto font-semibold tabular-nums text-foreground">{d.value}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
