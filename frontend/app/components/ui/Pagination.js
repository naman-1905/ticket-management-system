"use client";

import { ChevronLeft, ChevronRight } from "lucide-react";
import Button from "./Button";

export default function Pagination({ page, totalPages, onPageChange }) {
  if (totalPages <= 1) return null;

  return (
    <div className="mt-6 flex items-center justify-center gap-3 text-sm">
      <Button
        variant="secondary"
        disabled={page <= 1}
        onClick={() => onPageChange(page - 1)}
        aria-label="Previous page"
        className="px-2.5 py-2"
      >
        <ChevronLeft className="h-4 w-4" strokeWidth={2} />
      </Button>
      <span className="min-w-[6rem] text-center text-muted-foreground">
        Page {page} of {totalPages}
      </span>
      <Button
        variant="secondary"
        disabled={page >= totalPages}
        onClick={() => onPageChange(page + 1)}
        aria-label="Next page"
        className="px-2.5 py-2"
      >
        <ChevronRight className="h-4 w-4" strokeWidth={2} />
      </Button>
    </div>
  );
}
