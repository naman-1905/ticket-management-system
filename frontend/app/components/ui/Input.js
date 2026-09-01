const base =
  "w-full rounded-xl border border-border bg-surface px-3 py-2.5 text-sm text-foreground placeholder:text-muted-foreground transition-colors focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-accent/50";

export default function Input({ label, hint, className = "", id, ...props }) {
  const inputId = id || (label ? label.toLowerCase().replace(/\s+/g, "-") : undefined);

  return (
    <div>
      {label && (
        <label htmlFor={inputId} className="mb-1.5 block text-sm font-medium text-foreground">
          {label}
        </label>
      )}
      <input id={inputId} className={`${base} ${className}`} {...props} />
      {hint && <p className="mt-1 text-xs text-muted-foreground">{hint}</p>}
    </div>
  );
}
