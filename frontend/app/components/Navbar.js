"use client";

import { motion } from "framer-motion";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "../../lib/auth-context";
import BrandMark from "./ui/BrandMark";
import Button from "./ui/Button";
import ThemeToggle from "./ui/ThemeToggle";

function NavPill({ href, label, active }) {
  return (
    <Link
      href={href}
      className={`relative z-10 rounded-full px-3.5 py-1.5 text-sm font-medium transition-colors ${
        active ? "text-accent-foreground dark:text-foreground" : "text-muted-foreground hover:text-foreground"
      }`}
    >
      {active && (
        <motion.span
          layoutId="nav-pill"
          className="absolute inset-0 rounded-full bg-accent dark:border dark:border-accent/50 dark:bg-[#111827]"
          transition={{ type: "spring", stiffness: 400, damping: 30 }}
        />
      )}
      <span className="relative">{label}</span>
    </Link>
  );
}

export default function Navbar() {
  const { user, logout } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  if (!user) return null;

  async function handleLogout() {
    await logout();
    router.push("/login");
  }

  const links = [{ href: "/tickets", label: "Tickets" }];
  if (user.role === "AGENT" || user.role === "ADMIN") {
    links.push({ href: "/sla", label: "SLA Policies" });
  }
  if (user.role === "ADMIN") {
    links.push({ href: "/admin/users", label: "Users" });
    links.push({ href: "/admin/audit", label: "Audit Log" });
  }

  return (
    <header className="sticky top-0 z-20 border-b border-border bg-background/80 backdrop-blur-md">
      <div className="mx-auto flex h-16 max-w-5xl items-center justify-between gap-4 px-4">
        <div className="flex min-w-0 items-center gap-4">
          <BrandMark size="sm" />
          <nav className="flex max-w-full flex-wrap items-center gap-1 rounded-full border border-border bg-muted p-1">
            {links.map((link) => (
              <NavPill key={link.href} href={link.href} label={link.label} active={pathname === link.href} />
            ))}
          </nav>
        </div>

        <div className="flex shrink-0 items-center gap-2 sm:gap-3">
          <span className="hidden text-sm text-muted-foreground sm:inline">
            {user.full_name} · <span className="text-xs uppercase tracking-wide">{user.role}</span>
          </span>
          <ThemeToggle />
          <Button variant="ghost" onClick={handleLogout} className="px-3 py-1.5">
            Log out
          </Button>
        </div>
      </div>
    </header>
  );
}
