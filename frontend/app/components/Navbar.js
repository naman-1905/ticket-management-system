"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "../../lib/auth-context";

export default function Navbar() {
  const { user, logout } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  if (!user) return null;

  async function handleLogout() {
    await logout();
    router.push("/login");
  }

  const navLink = (href, label) => (
    <Link
      href={href}
      className={`text-sm font-medium px-3 py-2 rounded-md transition-colors ${
        pathname === href ? "bg-slate-900 text-white" : "text-slate-600 hover:bg-slate-100"
      }`}
    >
      {label}
    </Link>
  );

  return (
    <header className="border-b border-slate-200 bg-white sticky top-0 z-10">
      <div className="max-w-5xl mx-auto px-4 h-14 flex items-center justify-between">
        <nav className="flex items-center gap-1">
          <span className="font-semibold text-slate-900 mr-4">🎫 Tickets</span>
          {navLink("/tickets", "Tickets")}
          {(user.role === "AGENT" || user.role === "ADMIN") && navLink("/sla", "SLA Policies")}
          {user.role === "ADMIN" && navLink("/admin/users", "Users")}
          {user.role === "ADMIN" && navLink("/admin/audit", "Audit Log")}
        </nav>
        <div className="flex items-center gap-3">
          <span className="text-sm text-slate-500">
            {user.full_name} · <span className="uppercase text-xs">{user.role}</span>
          </span>
          <button onClick={handleLogout} className="text-sm font-medium text-slate-600 hover:text-red-600">
            Log out
          </button>
        </div>
      </div>
    </header>
  );
}
