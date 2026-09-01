const base =
  "rounded-xl border border-border bg-surface px-3 py-2.5 text-sm text-foreground transition-colors focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-accent/50";

export default function Select({ label, className = "", id, children, ...props }) {
  const selectId = id || (label ? label.toLowerCase().replace(/\s+/g, "-") : undefined);

  return (
    <div>
      {label && (
        <label htmlFor={selectId} className="mb-1.5 block text-sm font-medium text-foreground">
          {label}
        </label>
      )}
      <select id={selectId} className={`${base} ${className}`} {...props}>
        {children}
      </select>
    </div>
  );
}
