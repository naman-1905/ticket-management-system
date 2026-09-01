"use client";

import { useEffect, useRef, useState } from "react";
import { LogOut, Settings } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import Button from "./Button";
import ThemeToggle from "./ThemeToggle";

export default function SettingsMenu({ user, onLogout }) {
  const [open, setOpen] = useState(false);
  const ref = useRef(null);

  useEffect(() => {
    function handleClick(e) {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false);
    }
    if (open) document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, [open]);

  return (
    <div ref={ref} className="relative">
      <motion.button
        type="button"
        onClick={() => setOpen((v) => !v)}
        whileHover={{ scale: 1.05 }}
        whileTap={{ scale: 0.95 }}
        aria-label="Settings"
        aria-expanded={open}
        className="inline-flex h-9 w-9 items-center justify-center rounded-full border border-border bg-muted text-muted-foreground transition-colors hover:border-accent/40 hover:text-accent"
      >
        <Settings className="h-4 w-4" strokeWidth={2} />
      </motion.button>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: 6, scale: 0.97 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 6, scale: 0.97 }}
            transition={{ duration: 0.15 }}
            className="absolute right-0 top-full z-30 mt-2 w-56 overflow-hidden rounded-2xl border border-border bg-surface"
          >
            <div className="px-4 py-3">
              <p className="truncate text-sm font-semibold text-foreground">{user.full_name}</p>
              <p className="mt-0.5 text-xs uppercase tracking-wide text-muted-foreground">{user.role}</p>
            </div>

            <div className="border-t border-border px-3 py-2">
              <div className="flex items-center justify-between px-1 py-1.5">
                <span className="text-sm text-muted-foreground">Theme</span>
                <ThemeToggle />
              </div>
              <Button
                variant="ghost"
                onClick={() => {
                  setOpen(false);
                  onLogout();
                }}
                className="mt-1 w-full justify-start gap-2 px-2 py-2"
              >
                <LogOut className="h-4 w-4" strokeWidth={2} />
                Log out
              </Button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
