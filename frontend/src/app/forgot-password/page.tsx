"use client";

import Link from "next/link";
import { useState } from "react";

import { Button } from "@/components/ui/Button";
import { TextField } from "@/components/ui/TextField";
import { ApiError, forgotPassword } from "@/lib/api";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    try {
      // Same message whether or not the account exists, so this cannot be used
      // to discover who is registered.
      const detail = await forgotPassword(email);
      setMessage(detail);
    } catch (err) {
      setMessage(
        err instanceof ApiError
          ? err.message
          : "If that email has an account, a reset link is on its way.",
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-ink-50 px-6">
      <div className="w-full max-w-sm">
        <Link
          href="/"
          className="text-lg font-semibold tracking-tight text-navy-900"
        >
          SS <span className="text-gold-600">TUITIONS</span>
        </Link>

        <div className="mt-6 rounded-2xl border border-ink-200 bg-white p-8 shadow-[var(--shadow-card)]">
          <h1 className="text-xl font-semibold tracking-tight text-navy-900">
            Reset your password
          </h1>
          <p className="mt-1.5 text-sm text-ink-500">
            Enter your email and we will send you a link to set a new password.
          </p>

          {message ? (
            <div className="mt-6 rounded-lg border border-success-500/30 bg-success-50 px-4 py-3.5 text-sm text-success-700">
              {message}
            </div>
          ) : (
            <form onSubmit={submit} className="mt-6 space-y-4" noValidate>
              <TextField
                label="Email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
                autoComplete="email"
                required
                disabled={busy}
              />
              <Button type="submit" className="w-full" loading={busy}>
                Send reset link
              </Button>
            </form>
          )}

          <p className="mt-6 text-center text-sm text-ink-500">
            <Link href="/login" className="text-navy-700 hover:underline">
              Back to sign in
            </Link>
          </p>
        </div>
      </div>
    </main>
  );
}
