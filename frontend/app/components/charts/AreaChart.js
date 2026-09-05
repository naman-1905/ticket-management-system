"use client";

import { useEffect, useId, useMemo, useRef, useState } from "react";
import { motion } from "framer-motion";
import { AREA_SERIES } from "./palette";

const HEIGHT = 300;
const PAD = { top: 18, right: 20, bottom: 34, left: 40 };

// Fritsch–Carlson monotone cubic interpolation → smooth curve with no overshoot.
function monotonePath(pts) {
  const n = pts.length;
  if (n === 0) return "";
  if (n === 1) return `M ${pts[0].x} ${pts[0].y}`;

  const dx = [], m = [];
  for (let i = 0; i < n - 1; i++) {
    dx.push(pts[i + 1].x - pts[i].x);
    m.push((pts[i + 1].y - pts[i].y) / (pts[i + 1].x - pts[i].x));
  }

  const t = new Array(n).fill(0);
  t[0] = m[0];
  t[n - 1] = m[n - 2];
  for (let i = 1; i < n - 1; i++) {
    if (m[i - 1] * m[i] <= 0) {
      t[i] = 0;
    } else {
      const w1 = 2 * dx[i] + dx[i - 1];
      const w2 = dx[i] + 2 * dx[i - 1];
      t[i] = (w1 + w2) / (w1 / m[i - 1] + w2 / m[i]);
    }
  }

  let d = `M ${pts[0].x} ${pts[0].y}`;
  for (let i = 0; i < n - 1; i++) {
    const h = dx[i];
    const c1x = pts[i].x + h / 3;
    const c1y = pts[i].y + (t[i] * h) / 3;
    const c2x = pts[i + 1].x - h / 3;
    const c2y = pts[i + 1].y - (t[i + 1] * h) / 3;
    d += ` C ${c1x.toFixed(2)} ${c1y.toFixed(2)}, ${c2x.toFixed(2)} ${c2y.toFixed(2)}, ${pts[i + 1].x} ${pts[i + 1].y}`;
  }
  return d;
}

function niceScale(maxData) {
  const target = Math.max(1, maxData);
  const roughStep = target / 5;
  const exp = Math.floor(Math.log10(roughStep));
  const base = Math.pow(10, exp);
  const norm = roughStep / base;
  let f;
  if (norm <= 1) f = 1;
  else if (norm <= 2) f = 2;
  else if (norm <= 5) f = 5;
  else f = 10;
  let step = f * base;
  if (step < 1) step = 1;
  const maxVal = Math.ceil(target / step) * step;
  const ticks = [];
  for (let v = 0; v <= maxVal + 1e-9; v += step) ticks.push(v);
  return { maxVal, ticks };
}

function fmtDate(iso) {
  if (!iso) return "";
  const d = new Date(`${iso}T00:00:00`);
  return d.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

export default function AreaChart({ data }) {
  const containerRef = useRef(null);
  const svgRef = useRef(null);
  const gradId = useId().replace(/:/g, "");
  const [width, setWidth] = useState(0);
  const [hover, setHover] = useState(null);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const ro = new ResizeObserver((entries) => {
      setWidth(entries[0].contentRect.width);
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const n = data.length;
  const plotLeft = PAD.left;
  const plotRight = Math.max(plotLeft + 1, width - PAD.right);
  const plotTop = PAD.top;
  const plotBottom = HEIGHT - PAD.bottom;
  const plotWidth = plotRight - plotLeft;

  const { maxVal, ticks } = useMemo(() => {
    const all = data.flatMap((d) => [d.created, d.resolved]);
    return niceScale(Math.max(...all, 0));
  }, [data]);

  const xAt = (i) => (n <= 1 ? plotLeft + plotWidth / 2 : plotLeft + (i / (n - 1)) * plotWidth);
  const yAt = (v) => plotBottom - (v / maxVal) * (plotBottom - plotTop);

  const seriesPts = useMemo(
    () =>
      AREA_SERIES.map((s) => ({
        ...s,
        pts: data.map((d, i) => ({ x: xAt(i), y: yAt(d[s.key]) })),
      })),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [data, width]
  );

  const ready = width > 40 && n > 0;

  function handleMove(e) {
    if (!ready || !svgRef.current) return;
    const rect = svgRef.current.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const rel = (x - plotLeft) / plotWidth;
    let idx = Math.round(rel * (n - 1));
    idx = Math.max(0, Math.min(n - 1, idx));
    setHover(idx);
  }

  const labelStep = n > 0 ? Math.ceil(n / 6) : 1;
  const showLabel = (i) => i % labelStep === 0 || i === n - 1;

  if (!ready) {
    return <div ref={containerRef} style={{ height: HEIGHT }} className="w-full" />;
  }

  const hoverX = hover != null ? xAt(hover) : null;
  const tooltipTop = hover != null ? Math.min(yAt(data[hover].created), yAt(data[hover].resolved)) : 0;
  const tooltipLeft = hover != null ? Math.max(56, Math.min(width - 56, xAt(hover))) : 0;

  return (
    <div ref={containerRef} className="relative w-full select-none" style={{ height: HEIGHT }}>
      <svg
        ref={svgRef}
        width={width}
        height={HEIGHT}
        onMouseMove={handleMove}
        onMouseLeave={() => setHover(null)}
        className="block"
      >
        <defs>
          {AREA_SERIES.map((s) => (
            <linearGradient key={s.key} id={`${gradId}-${s.key}`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={s.color} stopOpacity={0.35} />
              <stop offset="60%" stopColor={s.color} stopOpacity={0.12} />
              <stop offset="100%" stopColor={s.color} stopOpacity={0} />
            </linearGradient>
          ))}
        </defs>

        {ticks.map((t) => (
          <g key={t}>
            <line
              x1={plotLeft}
              x2={plotRight}
              y1={yAt(t)}
              y2={yAt(t)}
              stroke="currentColor"
              className="text-border"
              strokeWidth={1}
              strokeDasharray={t === 0 ? undefined : "3 4"}
            />
            <text x={plotLeft - 10} y={yAt(t) + 4} textAnchor="end" className="fill-muted-foreground" style={{ fontSize: 11 }}>
              {t}
            </text>
          </g>
        ))}

        {data.map((d, i) =>
          showLabel(i) ? (
            <text key={i} x={xAt(i)} y={HEIGHT - 12} textAnchor="middle" className="fill-muted-foreground" style={{ fontSize: 11 }}>
              {fmtDate(d.date)}
            </text>
          ) : null
        )}

        {seriesPts.map((s) => {
          const line = monotonePath(s.pts);
          const area = `${line} L ${s.pts[s.pts.length - 1].x.toFixed(2)} ${plotBottom} L ${s.pts[0].x.toFixed(2)} ${plotBottom} Z`;
          return (
            <g key={s.key}>
              <motion.path
                d={area}
                fill={`url(#${gradId}-${s.key})`}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ duration: 0.8, delay: 0.25, ease: "easeOut" }}
              />
              <motion.path
                d={line}
                fill="none"
                stroke={s.color}
                strokeWidth={2.5}
                strokeLinecap="round"
                strokeLinejoin="round"
                initial={{ pathLength: 0, opacity: 0 }}
                animate={{ pathLength: 1, opacity: 1 }}
                transition={{ duration: 0.9, ease: "easeOut" }}
              />
            </g>
          );
        })}

        {seriesPts.map((s) => (
          <circle key={s.key} cx={s.pts[s.pts.length - 1].x} cy={s.pts[s.pts.length - 1].y} r={3.5} fill={s.color} />
        ))}

        {hover != null && (
          <g>
            <line
              x1={hoverX}
              x2={hoverX}
              y1={plotTop}
              y2={plotBottom}
              stroke="currentColor"
              className="text-muted-foreground/40"
              strokeWidth={1}
              strokeDasharray="3 3"
            />
            {seriesPts.map((s) => (
              <circle key={s.key} cx={hoverX} cy={yAt(data[hover][s.key])} r={4.5} fill={s.color} stroke="#fff" strokeWidth={1.5} />
            ))}
          </g>
        )}
      </svg>

      {hover != null && (
        <div
          className="pointer-events-none absolute z-10 -translate-x-1/2 -translate-y-full rounded-xl border border-border bg-surface px-3 py-2 shadow-lg"
          style={{ left: tooltipLeft, top: Math.max(8, tooltipTop - 14) }}
        >
          <p className="mb-1 text-xs font-medium text-muted-foreground">{fmtDate(data[hover].date)}</p>
          <div className="space-y-0.5">
            {AREA_SERIES.map((s) => (
              <div key={s.key} className="flex items-center gap-2 text-sm">
                <span className="inline-block h-2 w-2 rounded-full" style={{ background: s.color }} />
                <span className="text-muted-foreground">{s.label}</span>
                <span className="ml-auto pl-3 font-semibold tabular-nums text-foreground">{data[hover][s.key]}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
