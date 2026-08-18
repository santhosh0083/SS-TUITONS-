"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { Button } from "@/components/ui/Button";
import { TextField } from "@/components/ui/TextField";
import { ApiError, changePassword } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";

/**
 * Change-password screen. Used both for a voluntary change and for the forced
 * first-login change (when must_change_password is set). The layout guard sends
 * new accounts here and blocks everything else until it is done.
 */
export default function ChangePasswordPage() {
  const router = useRouter();
  const { user, refresh } = useAuth();
  const forced = user?.must_change_password ?? false;

  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);

    if (next.length < 10) {
      setError("New password must be at least 10 characters.");
      return;
    }
    if (next !== confirm) {
      setError("The two new passwords do not match.");
      return;
    }

    setBusy(true);
    try {
      await changePassword(current, next);
      // Changing the password revokes the session server-side, so send them to
      // sign in cleanly with the new one.
      await refresh();
      router.replace("/login?changed=1");
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "Could not change the password.",
      );
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto max-w-md">
      <div className="rounded-2xl border border-ink-200 bg-white p-8 shadow-[var(--shadow-card)]">
        <h1 className="text-xl font-semibold tracking-tight text-navy-900">
          {forced ? "Set your own password" : "Change your password"}
        </h1>
        <p className="mt-1.5 text-sm text-ink-500">
          {forced
            ? "You are signed in with a temporary password. Choose your own to continue."
            : "Enter your current password and a new one."}
        </p>

        <form onSubmit={submit} className="mt-6 space-y-4" noValidate>
          <TextField
            label={forced ? "Temporary password" : "Current password"}
            type="password"
            value={current}
            onChange={(e) => setCurrent(e.target.value)}
            autoComplete="current-password"
            required
            disabled={busy}
          />
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
            {forced ? "Set password and continue" : "Change password"}
          </Button>
        </form>
      </div>
    </div>
  );
}
