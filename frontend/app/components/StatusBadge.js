import { formatStatus } from "../../lib/format";

const STYLES = {
  NEW: "bg-sky-100 text-sky-700 dark:bg-sky-950 dark:text-sky-300",
  OPEN: "bg-blue-100 text-blue-700 dark:bg-blue-950 dark:text-blue-300",
  IN_PROGRESS: "bg-amber-100 text-amber-700 dark:bg-amber-950 dark:text-amber-300",
  WAITING_FOR_CUSTOMER: "bg-violet-100 text-violet-700 dark:bg-violet-950 dark:text-violet-300",
  WAITING_FOR_INTERNAL: "bg-fuchsia-100 text-fuchsia-700 dark:bg-fuchsia-950 dark:text-fuchsia-300",
  ON_HOLD: "bg-stone-200 text-stone-700 dark:bg-stone-800 dark:text-stone-300",
  RESOLVED: "bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300",
  CLOSED: "bg-stone-100 text-stone-500 dark:bg-stone-900 dark:text-stone-400",
  CANCELLED: "bg-red-100 text-red-600 dark:bg-red-950 dark:text-red-300",
};

export default function StatusBadge({ status }) {
  return (
    <span
      className={`whitespace-nowrap rounded-full px-2.5 py-1 text-xs font-medium ${STYLES[status] || "bg-muted text-muted-foreground"}`}
    >
      {formatStatus(status)}
    </span>
  );
}
