"use client";

import { useState } from "react";

import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { ApiError, apiFetch } from "@/lib/api";

/**
 * Removes a student, parent or tutor from the dashboard, or brings them back.
 *
 * Deliberately not a delete. Fee records, attendance and past classes point at
 * these people, so removing the row would leave that history dangling -- a
 * parent who leaves in March still paid in January. The account is suspended:
 * hidden from the lists, signed out, and stripped of the assignments that
 * grant access.
 *
 * The confirmation is a plain step rather than a scary one, because this is a
 * routine action that happens whenever a family stops attending, and it can be
 * undone.
 */
export function RemovePersonButton({
  userId,
  fullName,
  removed,
  onDone,
}: {
  userId: string;
  fullName: string;
  removed: boolean;
  onDone: () => void;
}) {
  const [confirming, setConfirming] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function act() {
    setBusy(true);
    setError(null);
    try {
      await apiFetch(`/admin/users/${userId}/${removed ? "restore" : "remove"}`, {
        method: "POST",
      });
      setConfirming(false);
      onDone();
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : `Could not ${removed ? "restore" : "remove"} ${fullName}.`,
      );
    } finally {
      setBusy(false);
    }
  }

  if (removed) {
    return (
      <button
        type="button"
        onClick={act}
        disabled={busy}
        className="rounded-lg px-2.5 py-1.5 text-sm font-medium text-navy-700 transition-colors hover:bg-navy-50 disabled:opacity-50"
      >
        {busy ? "Restoring…" : "Restore"}
      </button>
    );
  }

  return (
    <>
      <button
        type="button"
        onClick={() => setConfirming(true)}
        className="rounded-lg px-2.5 py-1.5 text-sm font-medium text-ink-500 transition-colors hover:bg-danger-50 hover:text-danger-700"
      >
        Remove
      </button>

      <Modal
        open={confirming}
        title={`Remove ${fullName}?`}
        description="They come off the dashboard and can no longer sign in."
        onClose={() => setConfirming(false)}
      >
        <div className="space-y-4">
          <div className="rounded-lg border border-ink-200 bg-ink-50 px-3.5 py-3 text-sm text-ink-600">
            <p className="font-medium text-ink-800">Their records are kept.</p>
            <p className="mt-1">
              Fees, attendance and past classes stay exactly as they are, so
              your history stays correct. You can restore them at any time.
            </p>
          </div>

          {error && (
            <div
              role="alert"
              className="rounded-lg border border-danger-500/25 bg-danger-50 px-3.5 py-3 text-sm text-danger-700"
            >
              {error}
            </div>
          )}

          <div className="flex gap-3">
            <Button
              type="button"
              variant="secondary"
              className="flex-1"
              onClick={() => setConfirming(false)}
              disabled={busy}
            >
              Cancel
            </Button>
            <Button
              type="button"
              className="flex-1"
              onClick={act}
              loading={busy}
            >
              Remove
            </Button>
          </div>
        </div>
      </Modal>
    </>
  );
}
