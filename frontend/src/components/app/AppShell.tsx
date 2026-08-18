"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useState, type ReactNode } from "react";

import { useAuth } from "@/lib/auth-context";

interface NavItem {
  href: string;
  label: string;
  icon: ReactNode;
}

const NAV_BY_ROLE: Record<string, NavItem[]> = {
  ADMIN: [
    { href: "/admin", label: "Overview", icon: <path d="M4 5h6v6H4V5Zm10 0h6v4h-6V5ZM4 15h6v4H4v-4Zm10-2h6v6h-6v-6Z" /> },
    { href: "/admin/students", label: "Students", icon: <path d="M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8Zm-8 8a8 8 0 0 1 16 0" /> },
    { href: "/admin/parents", label: "Parents", icon: <path d="M8 11a3 3 0 1 0 0-6 3 3 0 0 0 0 6Zm8 0a3 3 0 1 0 0-6 3 3 0 0 0 0 6ZM2 20a6 6 0 0 1 12 0m-2-9a6 6 0 0 1 10 9" /> },
    { href: "/admin/tutors", label: "Tutors", icon: <path d="M12 3 2 8l10 5 10-5-10-5Zm0 9.5L5 9v4.5c0 2 3.1 3.5 7 3.5s7-1.5 7-3.5V9" /> },
    { href: "/admin/batches", label: "Batches", icon: <path d="M4 6h16M4 12h16M4 18h16" /> },
    { href: "/admin/classes", label: "Classes", icon: <path d="M8 2v4m8-4v4M3 9h18M5 5h14a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2Z" /> },
    { href: "/admin/content", label: "Study material", icon: <path d="M4 4h9l7 7v9a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V5a1 1 0 0 1 1-1Zm9 0v7h7" /> },
    { href: "/admin/payments", label: "Fees", icon: <path d="M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18Zm3-12H10.5a2 2 0 0 0 0 4h3a2 2 0 0 1 0 4H9" /> },
    { href: "/messages", label: "Messages", icon: <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2v10Z" /> },
  ],
  TUTOR: [
    { href: "/tutor", label: "My classes", icon: <path d="M8 2v4m8-4v4M3 9h18M5 5h14a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2Z" /> },
    { href: "/tutor/attendance", label: "Attendance", icon: <path d="M9 11l3 3 7-7M20 12v7a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V5a1 1 0 0 1 1-1h9" /> },
    { href: "/messages", label: "Messages", icon: <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2v10Z" /> },
  ],
  PARENT: [
    { href: "/parent", label: "Overview", icon: <path d="M4 5h6v6H4V5Zm10 0h6v4h-6V5ZM4 15h6v4H4v-4Zm10-2h6v6h-6v-6Z" /> },
    { href: "/messages", label: "Messages", icon: <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2v10Z" /> },
    { href: "/parent/fees", label: "Fees", icon: <path d="M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18Zm3-12H10.5a2 2 0 0 0 0 4h3a2 2 0 0 1 0 4H9" /> },
  ],
  STUDENT: [
    { href: "/student", label: "Today", icon: <path d="M8 2v4m8-4v4M3 9h18M5 5h14a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2Z" /> },
    { href: "/student/material", label: "Study material", icon: <path d="M4 4h9l7 7v9a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V5a1 1 0 0 1 1-1Zm9 0v7h7" /> },
    { href: "/student/tests", label: "Tests", icon: <path d="M9 11l3 3 7-7M20 12v7a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V5a1 1 0 0 1 1-1h9" /> },
  ],
};

function primaryRole(roles: string[], isSuperadmin: boolean): string {
  if (isSuperadmin || roles.includes("ADMIN")) return "ADMIN";
  return roles.find((r) => r in NAV_BY_ROLE) ?? "STUDENT";
}

function initials(name: string): string {
  return name
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((w) => w[0]?.toUpperCase())
    .join("");
}

export function AppShell({ children }: { children: ReactNode }) {
  const { user, signOut } = useAuth();
  const pathname = usePathname();
  const router = useRouter();
  const [menuOpen, setMenuOpen] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);

  if (!user) return null;

  const role = primaryRole([...user.roles], user.is_superadmin);
  const nav = NAV_BY_ROLE[role] ?? [];

  async function handleSignOut() {
    await signOut();
    router.push("/login");
  }

  return (
    <div className="flex min-h-screen bg-ink-50">
      {/* Backdrop for the mobile drawer */}
      {sidebarOpen && (
        <button
          type="button"
          aria-label="Close navigation"
          onClick={() => setSidebarOpen(false)}
          className="fixed inset-0 z-30 animate-[var(--animate-fade-in)] bg-navy-950/40 lg:hidden"
        />
      )}

      {/* ---------- Sidebar ---------- */}
      <aside
        className={[
          "fixed inset-y-0 left-0 z-40 flex w-64 flex-col bg-navy-900 transition-transform duration-200 ease-[var(--ease-out-soft)]",
          sidebarOpen ? "translate-x-0" : "-translate-x-full",
          "lg:translate-x-0",
        ].join(" ")}
      >
        <div className="flex h-16 items-center px-6">
          <Link href="/" className="text-lg font-semibold tracking-tight text-white">
            SS <span className="text-gold-400">TUITIONS</span>
          </Link>
        </div>

        <nav className="flex-1 space-y-0.5 px-3 py-4">
          {nav.map((item) => {
            const active =
              pathname === item.href ||
              (item.href !== `/${role.toLowerCase()}` &&
                pathname.startsWith(`${item.href}/`));
            return (
              <Link
                key={item.href}
                href={item.href}
                onClick={() => setSidebarOpen(false)}
                aria-current={active ? "page" : undefined}
                className={[
                  "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition-colors duration-150",
                  active
                    ? "bg-white/10 font-medium text-white"
                    : "text-navy-200 hover:bg-white/5 hover:text-white",
                ].join(" ")}
              >
                <svg
                  className="h-[18px] w-[18px] shrink-0"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.6"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  aria-hidden="true"
                >
                  {item.icon}
                </svg>
                {item.label}
              </Link>
            );
          })}
        </nav>

        <div className="border-t border-white/10 p-3">
          <div className="rounded-lg px-3 py-2 text-xs text-navy-300">
            Signed in as
            <div className="mt-0.5 truncate text-sm text-white">{user.full_name}</div>
          </div>
        </div>
      </aside>

      {/* ---------- Main column ---------- */}
      <div className="flex min-w-0 flex-1 flex-col lg:pl-64">
        <header className="sticky top-0 z-20 flex h-16 items-center justify-between border-b border-ink-200 bg-white/90 px-5 backdrop-blur-md">
          <button
            type="button"
            onClick={() => setSidebarOpen(true)}
            aria-label="Open navigation"
            className="lg:hidden"
          >
            <svg
              className="h-6 w-6 text-navy-900"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              viewBox="0 0 24 24"
              aria-hidden="true"
            >
              <path strokeLinecap="round" d="M4 7h16M4 12h16M4 17h16" />
            </svg>
          </button>

          <div className="hidden lg:block" />

          <div className="relative">
            <button
              type="button"
              onClick={() => setMenuOpen((v) => !v)}
              aria-expanded={menuOpen}
              aria-haspopup="menu"
              className="flex items-center gap-2.5 rounded-lg px-2 py-1.5 transition-colors hover:bg-ink-100"
            >
              <span className="flex h-8 w-8 items-center justify-center rounded-full bg-navy-900 text-xs font-semibold text-white">
                {initials(user.full_name)}
              </span>
              <span className="hidden text-sm font-medium text-ink-800 sm:block">
                {user.full_name}
              </span>
            </button>

            {menuOpen && (
              <div
                role="menu"
                className="absolute right-0 mt-2 w-56 animate-[var(--animate-scale-in)] origin-top-right rounded-xl border border-ink-200 bg-white p-1.5 shadow-[var(--shadow-lifted)]"
              >
                <div className="px-3 py-2">
                  <p className="truncate text-sm font-medium text-ink-900">
                    {user.full_name}
                  </p>
                  <p className="truncate text-xs text-ink-500">{user.email}</p>
                  <p className="mt-1.5 inline-block rounded bg-navy-50 px-1.5 py-0.5 text-[11px] font-medium text-navy-700">
                    {user.is_superadmin ? "Owner" : role}
                  </p>
                </div>
                <hr className="my-1 border-ink-200" />
                <button
                  type="button"
                  role="menuitem"
                  onClick={handleSignOut}
                  className="w-full rounded-lg px-3 py-2 text-left text-sm text-danger-700 transition-colors hover:bg-danger-50"
                >
                  Sign out
                </button>
              </div>
            )}
          </div>
        </header>

        <main className="flex-1 px-5 py-8">{children}</main>
      </div>
    </div>
  );
}
