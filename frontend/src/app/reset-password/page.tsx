"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";

import { Button } from "@/components/ui/Button";
import { TextField } from "@/components/ui/TextField";
import { ApiError, resetPassword } from "@/lib/api";

function ResetForm() {
  const router = useRouter();
  const params = useSearchParams();
  const token = params.get("token") ?? "";

  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    if (next.length < 10) {
      setError("Password must be at least 10 characters.");
      return;
    }
    if (next !== confirm) {
      setError("The two passwords do not match.");
      return;
    }
    setBusy(true);
    try {
      await resetPassword(token, next);
      router.replace("/login?reset=1");
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "Could not reset the password.",
      );
      setBusy(false);
    }
  }

  if (!token) {
    return (
      <div className="rounded-lg border border-danger-500/25 bg-danger-50 px-4 py-3.5 text-sm text-danger-700">
        This reset link is incomplete. Please request a new one from the{" "}
        <Link href="/forgot-password" className="underline">
          forgot password
        </Link>{" "}
        page.
      </div>
    );
  }

  return (
    <form onSubmit={submit} className="space-y-4" noValidate>
      <TextField
        label="New password"
        type="password"
        value={next}
        onChange={(e) => setNext(e.target.value)}
        hint="At least 10 characters."
        autoComplete="new-password"
        required
        disabled={busy}
      />
      <TextField
        label="Confirm new password"
        type="password"
        value={confirm}
        onChange={(e) => setConfirm(e.target.value)}
        autoComplete="new-password"
        required
        disabled={busy}
      />
      {error && (
        <div
          role="alert"
          className="rounded-lg border border-danger-500/25 bg-danger-50 px-3.5 py-3 text-sm text-danger-700"
        >
          {error}
        </div>
      )}
      <Button type="submit" className="w-full" loading={busy}>
        Set new password
      </Button>
    </form>
  );
}

export default function ResetPasswordPage() {
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
            Choose a new password
          </h1>
          <p className="mt-1.5 mb-6 text-sm text-ink-500">
            Enter a new password for your SS Tuitions account.
          </p>
          <Suspense fallback={<p className="text-sm text-ink-500">Loading…</p>}>
            <ResetForm />
          </Suspense>
        </div>
      </div>
    </main>
  );
}
