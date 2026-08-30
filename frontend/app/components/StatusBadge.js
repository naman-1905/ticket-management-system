const STYLES = {
  OPEN: "bg-blue-100 text-blue-700",
  IN_PROGRESS: "bg-amber-100 text-amber-700",
  ON_HOLD: "bg-slate-200 text-slate-700",
  RESOLVED: "bg-emerald-100 text-emerald-700",
  CLOSED: "bg-slate-100 text-slate-500",
};

export default function StatusBadge({ status }) {
  return (
    <span className={`text-xs font-medium px-2 py-1 rounded-full whitespace-nowrap ${STYLES[status] || "bg-slate-100 text-slate-600"}`}>
      {status.replace("_", " ")}
    </span>
  );
}
