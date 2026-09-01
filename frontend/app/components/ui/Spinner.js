"use client";

import { Loader2 } from "lucide-react";

export default function Spinner({ label = "Loading…" }) {
  return (
    <div className="flex items-center gap-3 text-sm text-muted-foreground">
      <Loader2 className="h-4 w-4 animate-spin text-accent" strokeWidth={2} />
      {label}
    </div>
  );
}
