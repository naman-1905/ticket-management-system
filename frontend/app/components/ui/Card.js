export function Card({ children, className = "" }) {
  return (
    <div className={`rounded-3xl border border-border bg-surface p-5 ${className}`}>{children}</div>
  );
}

export function ListPanel({ children, className = "" }) {
  return (
    <div className={`overflow-hidden rounded-3xl border border-border bg-surface divide-y divide-border ${className}`}>
      {children}
    </div>
  );
}
