"use client";

import { useState } from "react";

interface Credential {
  label: string;
  email: string;
  password: string;
}

/**
 * Shows newly created sign-in details exactly once.
 *
 * The password is generated server-side and only its hash is stored, so this
 * is genuinely the single opportunity to capture it. The UI says so plainly
 * rather than letting an admin close the dialog and discover it later.
 */
export function CredentialsPanel({
  credentials,
  onDone,
}: {
  credentials: Credential[];
  onDone: () => void;
}) {
  const [copied, setCopied] = useState(false);

  const asText = credentials
    .map((c) => `${c.label}\nEmail: ${c.email}\nPassword: ${c.password}`)
    .join("\n\n");

  async function copyAll() {
    try {
      await navigator.clipboard.writeText(asText);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Clipboard can be blocked; the details are on screen regardless.
    }
  }

  return (
    <div>
      <div className="rounded-lg border border-warning-500/35 bg-warning-50 px-4 py-3 text-sm text-warning-700">
        <strong className="font-semibold">Copy these now.</strong> Passwords are
        stored only as a hash and cannot be shown again. If lost, you will have
        to reset them.
      </div>

      <div className="mt-4 space-y-3">
        {credentials.map((c) => (
          <div key={c.email} className="rounded-lg border border-ink-200 p-4">
            <p className="text-xs font-semibold uppercase tracking-wider text-ink-500">
              {c.label}
            </p>
            <dl className="mt-2.5 space-y-1.5 text-sm">
              <div className="flex gap-2">
                <dt className="w-20 shrink-0 text-ink-500">Email</dt>
                <dd className="min-w-0 break-all font-medium text-ink-900">
                  {c.email}
                </dd>
              </div>
              <div className="flex gap-2">
                <dt className="w-20 shrink-0 text-ink-500">Password</dt>
                <dd className="min-w-0 break-all font-mono font-medium text-ink-900">
                  {c.password}
                </dd>
              </div>
            </dl>
          </div>
        ))}
      </div>

      <div className="mt-5 flex flex-col gap-2 sm:flex-row">
        <button
          type="button"
          onClick={copyAll}
          className="inline-flex h-11 flex-1 items-center justify-center gap-2 rounded-lg border border-ink-300 px-4 text-sm font-medium text-navy-900 transition-colors hover:bg-ink-50"
        >
          {copied ? "Copied" : "Copy all details"}
        </button>
        <button
          type="button"
          onClick={onDone}
          className="inline-flex h-11 flex-1 items-center justify-center rounded-lg bg-navy-900 px-4 text-sm font-medium text-white transition-colors hover:bg-navy-800"
        >
          Done
        </button>
      </div>
    </div>
  );
}
