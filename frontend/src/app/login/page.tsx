"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { Button } from "@/components/ui/Button";
import { TextField } from "@/components/ui/TextField";
import { ApiError, login } from "@/lib/api";

/** Where each role lands after signing in. */
const HOME_BY_ROLE: Record<string, string> = {
  ADMIN: "/admin",
  TUTOR: "/tutor",
  PARENT: "/parent",
  STUDENT: "/student",
};

export default function LoginPage() {
  const router = useRouter();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  // Incremented on each failure so the shake animation replays every time,
  // not just the first.
  const [failureCount, setFailureCount] = useState(0);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);

    try {
      const user = await login(email, password);
      const primaryRole = user.is_superadmin
        ? "ADMIN"
        : (user.roles.find((r) => r in HOME_BY_ROLE) ?? "");
      router.push(HOME_BY_ROLE[primaryRole] ?? "/");
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : "Could not reach the server. Check your connection and try again.",
      );
      setFailureCount((n) => n + 1);
      setSubmitting(false);
    }
  }

  return (
    <main className="flex min-h-screen">
      {/* ---------- Brand panel (hidden on small screens) ---------- */}
      <section className="relative hidden w-1/2 flex-col justify-between bg-navy-900 p-12 lg:flex">
        <div className="animate-[var(--animate-fade-in)]">
          <span className="text-xl font-semibold tracking-tight text-white">
            SS <span className="text-gold-400">TUITIONS</span>
          </span>
        </div>

        <div className="max-w-md animate-[var(--animate-fade-up)]">
          <h1 className="text-4xl font-semibold leading-tight tracking-tight text-white">
            Focused preparation for Grade 11 &amp; 12.
          </h1>
          <p className="mt-5 text-[15px] leading-relaxed text-navy-200">
            JEE, NEET, EAMCET, IPE and SAT — small batches and one-to-one
            teaching, with progress you can actually see.
          </p>

          <ul className="mt-10 space-y-3.5">
            {[
              "Live classes with IIT tutors",
              "Topic-wise tests and worksheets",
              "Attendance and progress for parents",
            ].map((item, i) => (
              <li
                key={item}
                className="flex items-center gap-3 text-sm text-navy-100 animate-[var(--animate-fade-up)]"
                style={{ animationDelay: `${120 + i * 90}ms` }}
              >
                <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-gold-400/15">
                  <svg
                    className="h-3 w-3 text-gold-400"
                    viewBox="0 0 20 20"
                    fill="currentColor"
                    aria-hidden="true"
                  >
                    <path
                      fillRule="evenodd"
                      d="M16.7 5.3a1 1 0 010 1.4l-7.5 7.5a1 1 0 01-1.4 0L3.3 9.7a1 1 0 111.4-1.4l3.8 3.8 6.8-6.8a1 1 0 011.4 0z"
                      clipRule="evenodd"
                    />
                  </svg>
                </span>
                {item}
              </li>
            ))}
          </ul>
        </div>

        <p className="text-xs text-navy-300">
          © {new Date().getFullYear()} SS Tuitions
        </p>
      </section>

      {/* ---------- Sign-in form ---------- */}
      <section className="flex w-full items-center justify-center px-6 py-12 lg:w-1/2">
        <div className="w-full max-w-sm animate-[var(--animate-fade-up)]">
          <div className="mb-8 lg:hidden">
            <span className="text-lg font-semibold tracking-tight text-navy-900">
              SS <span className="text-gold-600">TUITIONS</span>
            </span>
          </div>

          <h2 className="text-2xl font-semibold tracking-tight text-navy-900">
            Sign in
          </h2>
          <p className="mt-1.5 text-sm text-ink-500">
            Use the details SS Tuitions gave you.
          </p>

          <form onSubmit={handleSubmit} className="mt-8 space-y-5" noValidate>
            <TextField
              label="Email"
              type="email"
              name="email"
              autoComplete="email"
              placeholder="you@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              disabled={submitting}
            />

            <TextField
              label="Password"
              type="password"
              name="password"
              autoComplete="current-password"
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              disabled={submitting}
            />

            {error && (
              <div
                key={failureCount}
                // `role="alert"` makes a screen reader announce this the moment
                // it appears, rather than leaving the user waiting in silence.
                role="alert"
                className="animate-[var(--animate-shake)] rounded-lg border border-danger-500/25 bg-danger-50 px-3.5 py-3 text-sm text-danger-700"
              >
                {error}
              </div>
            )}

            <Button
              type="submit"
              size="lg"
              loading={submitting}
              className="w-full"
            >
              {submitting ? "Signing in…" : "Sign in"}
            </Button>
          </form>

          <p className="mt-8 text-center text-xs leading-relaxed text-ink-500">
            Trouble signing in? Contact SS Tuitions and we will reset your
            password.
          </p>
        </div>
      </section>
    </main>
  );
}
