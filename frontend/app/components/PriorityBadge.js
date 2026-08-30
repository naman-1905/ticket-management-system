const STYLES = {
  P1: "bg-red-100 text-red-700",
  P2: "bg-orange-100 text-orange-700",
  P3: "bg-yellow-100 text-yellow-700",
  P4: "bg-slate-100 text-slate-600",
};

export default function PriorityBadge({ priority }) {
  return (
    <span className={`text-xs font-semibold px-2 py-1 rounded-full ${STYLES[priority] || "bg-slate-100 text-slate-600"}`}>
      {priority}
    </span>
  );
}
