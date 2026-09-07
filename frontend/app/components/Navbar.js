"use client";

import { useEffect, useState } from "react";
import { ArrowUpRight, Menu, X } from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { AnimatePresence, motion } from "framer-motion";
import { useAuth } from "../../lib/auth-context";
import { hasPermission, isStaff } from "../../lib/permissions";
import BrandMark from "./ui/BrandMark";
import SettingsMenu from "./ui/SettingsMenu";

function NavPill({ href, label, active, onClick }) {
  return (
    <Link
      href={href}
      onClick={onClick}
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

function NavBarInner({ children, className = "" }) {
  return (
    <header className="sticky top-0 z-50 w-full border-b border-border/60 bg-background/95 backdrop-blur-md supports-[backdrop-filter]:bg-background/80">
      <div className={`mx-auto flex w-full max-w-5xl flex-col px-3 py-3 sm:px-4 sm:py-4 ${className}`}>
        {children}
      </div>
    </header>
  );
}

function NavShell({ brand, nav, actions }) {
  return (
    <div className="grid w-full grid-cols-[auto_1fr_auto] items-center gap-2 sm:gap-3">
      <div className="shrink-0">{brand}</div>
      <div className="min-w-0 flex items-center justify-center">{nav}</div>
      <div className="flex shrink-0 items-center justify-end gap-1.5 sm:gap-2">{actions}</div>
    </div>
  );
}

export default function Navbar() {
  const { user, logout } = useAuth();
  const router = useRouter();
  const pathname = usePathname();
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => {
    setMobileOpen(false);
  }, [pathname]);

  useEffect(() => {
    if (!mobileOpen) return;
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = prev;
    };
  }, [mobileOpen]);

  if (!user) {
    return (
      <NavBarInner>
        <NavShell
          brand={<BrandMark />}
          nav={null}
          actions={
            <>
              <Link href="/login">
                <button className="rounded-full px-3 py-2 text-sm font-medium text-muted-foreground transition-colors hover:text-foreground sm:px-4">
                  Login
                </button>
              </Link>
              <Link href="/register">
                <button className="rounded-full bg-accent px-3 py-2 text-sm font-medium text-accent-foreground transition-colors hover:opacity-90 sm:px-4">
                  Register
                </button>
              </Link>
            </>
          }
        />
      </NavBarInner>
    );
  }

  async function handleLogout() {
    await logout();
    router.push("/login");
  }

  const staff = isStaff(user);
  const links = staff
    ? [
        { href: "/dashboard", label: "Dashboard" },
        { href: "/tickets", label: "Tickets" },
      ]
    : [
        { href: "/portal/tickets", label: "My tickets" },
        { href: "/portal/kb", label: "Help" },
      ];

  if (staff && hasPermission(user, "sla.view")) {
    links.push({ href: "/sla", label: "SLA" });
  }
  if (staff && hasPermission(user, "organization.manage")) {
    links.push({ href: "/customers", label: "Customers" });
  }
  if (hasPermission(user, "user.manage")) {
    links.push({ href: "/admin/users", label: "Users" });
  }
  if (hasPermission(user, "audit.view")) {
    links.push({ href: "/admin/audit", label: "Audit" });
  }

  const closeMobile = () => setMobileOpen(false);

  return (
    <NavBarInner>
      <NavShell
        brand={<BrandMark />}
        nav={
          <nav className="hidden items-center justify-center gap-1.5 md:flex md:flex-wrap">
            {links.map((link) => (
              <NavPill key={link.href} href={link.href} label={link.label} active={pathname === link.href} />
            ))}
          </nav>
        }
        actions={
          <>
            <button
              type="button"
              onClick={() => setMobileOpen((v) => !v)}
              aria-label={mobileOpen ? "Close menu" : "Open menu"}
              aria-expanded={mobileOpen}
              className="inline-flex h-9 w-9 items-center justify-center rounded-full border border-border bg-muted text-muted-foreground transition-colors hover:border-accent/40 hover:text-accent md:hidden"
            >
              {mobileOpen ? <X className="h-4 w-4" strokeWidth={2} /> : <Menu className="h-4 w-4" strokeWidth={2} />}
            </button>
            <SettingsMenu user={user} onLogout={handleLogout} />
          </>
        }
      />

      <AnimatePresence>
        {mobileOpen && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden md:hidden"
          >
            <nav className="mt-2 flex flex-col gap-1.5 border-t border-border/60 pt-2 md:hidden">
              {links.map((link) => (
                <NavPill
                  key={link.href}
                  href={link.href}
                  label={link.label}
                  active={pathname === link.href}
                  onClick={closeMobile}
                />
              ))}
            </nav>
          </motion.div>
        )}
      </AnimatePresence>
    </NavBarInner>
  );
}
