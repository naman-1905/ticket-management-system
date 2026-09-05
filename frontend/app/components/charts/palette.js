// Shared color palettes for dashboard charts.
// Hex values are chosen to read well on both light (#ffffff) and dark (#1a1a1a) surfaces,
// and stay consistent with StatusBadge / PriorityBadge semantics.

export const STATUS_COLORS = {
  NEW: "#0ea5e9", // sky
  OPEN: "#3b82f6", // blue
  IN_PROGRESS: "#f59e0b", // amber
  WAITING_FOR_CUSTOMER: "#8b5cf6", // violet
  WAITING_FOR_INTERNAL: "#d946ef", // fuchsia
  ON_HOLD: "#a8a29e", // stone
  RESOLVED: "#10b981", // emerald
  CLOSED: "#78716c", // stone-dark
  CANCELLED: "#ef4444", // red
};

export const PRIORITY_COLORS = {
  P1: "#ef4444", // red
  P2: "#f97316", // orange
  P3: "#eab308", // yellow
  P4: "#a8a29e", // stone
};

// Hero time-series series. "created" uses the app accent (orange), "resolved" emerald.
export const AREA_SERIES = [
  { key: "created", label: "Created", color: "#f97316" },
  { key: "resolved", label: "Resolved", color: "#10b981" },
];
