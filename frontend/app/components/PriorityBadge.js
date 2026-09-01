const STYLES = {
  P1: "bg-red-100 text-red-700 dark:bg-red-950 dark:text-red-300",
  P2: "bg-orange-100 text-orange-700 dark:bg-orange-950 dark:text-orange-300",
  P3: "bg-yellow-100 text-yellow-800 dark:bg-yellow-950 dark:text-yellow-300",
  P4: "bg-stone-100 text-stone-600 dark:bg-stone-900 dark:text-stone-400",
};

export default function PriorityBadge({ priority }) {
  return (
    <span
      className={`rounded-full px-2.5 py-1 text-xs font-semibold ${STYLES[priority] || "bg-muted text-muted-foreground"}`}
    >
      {priority}
    </span>
  );
}
