"use client";

import { useRouter } from "next/navigation";
import { useEffect, type ReactNode } from "react";

import { AppShell } from "@/components/app/AppShell";
import { AuthProvider, useAuth } from "@/lib/auth-context";

/**
 * Guard for every signed-in page.
 *
 * This is a convenience layer, not the security boundary. It stops a signed-out
 * visitor seeing an empty shell — but anyone can edit client-side JavaScript, so
 * the real enforcement is server-side: every API route checks the caller's role
 * and every student-data query passes through the visibility layer. A user who
 * bypassed this would reach pages that return 401 and 403.
 */
function Guard({ children }: { children: ReactNode }) {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    // Wait for the session restore to finish, otherwise a signed-in user is
    // redirected to /login on every page refresh.
    if (!loading && !user) router.replace("/login");
  }, [loading, user, router]);

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-ink-50">
        <div className="flex flex-col items-center gap-3">
          <svg
            className="h-6 w-6 animate-spin text-navy-500"
            viewBox="0 0 24 24"
            fill="none"
            aria-hidden="true"
          >
            <circle
              className="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              strokeWidth="3"
            />
            <path
              className="opacity-90"
              fill="currentColor"
              d="M4 12a8 8 0 018-8v3a5 5 0 00-5 5H4z"
            />
          </svg>
          <p className="text-sm text-ink-500">Loading…</p>
          <span className="sr-only" role="status">
            Checking your session
          </span>
        </div>
      </div>
    );
  }

  if (!user) return null; // redirect is in flight

  return <AppShell>{children}</AppShell>;
}

export default function AppLayout({ children }: { children: ReactNode }) {
  return (
    <AuthProvider>
      <Guard>{children}</Guard>
    </AuthProvider>
  );
}
