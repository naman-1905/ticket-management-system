const base =
  "w-full rounded-xl border border-border bg-surface px-3 py-2.5 text-sm text-foreground placeholder:text-muted-foreground transition-colors focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-accent/50 resize-y";

export default function Textarea({ label, className = "", id, ...props }) {
  const textareaId = id || (label ? label.toLowerCase().replace(/\s+/g, "-") : undefined);

  return (
    <div>
      {label && (
        <label htmlFor={textareaId} className="mb-1.5 block text-sm font-medium text-foreground">
          {label}
        </label>
      )}
      <textarea id={textareaId} className={`${base} ${className}`} {...props} />
    </div>
  );
}
