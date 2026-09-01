"use client";

import { ArrowUpRight } from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "../../lib/auth-context";
import BrandMark from "./ui/BrandMark";
import SettingsMenu from "./ui/SettingsMenu";

function NavPill({ href, label, active }) {
  return (
    <Link
      href={href}
      className={`inline-flex items-center gap-1 rounded-full px-3.5 py-2 text-sm font-medium transition-all ${
        active
          ? "bg-accent text-accent-foreground"
          : "border border-border text-muted-foreground hover:border-foreground/20 hover:bg-muted hover:text-foreground"
      }`}
    >
      <span>{label}</span>
      {!active && <ArrowUpRight className="h-3.5 w-3.5 opacity-60" strokeWidth={2} />}
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
    <header className="sticky top-0 z-20 flex justify-center px-4 py-4">
      <div className="grid w-full max-w-5xl grid-cols-[auto_1fr_auto] items-center gap-3 rounded-[2rem] bg-surface px-4 py-2.5 backdrop-blur-md dark:bg-background">
        <div className="shrink-0">
          LOGO
        </div>

        <nav className="flex flex-wrap items-center justify-center gap-1.5">
          {links.map((link) => (
            <NavPill key={link.href} href={link.href} label={link.label} active={pathname === link.href} />
          ))}
        </nav>

        <div className="shrink-0 justify-self-end">
          <SettingsMenu user={user} onLogout={handleLogout} />
        </div>
      </div>
    </header>
  );
}
