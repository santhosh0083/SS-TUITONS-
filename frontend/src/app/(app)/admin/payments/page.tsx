"use client";

import { useCallback, useEffect, useState } from "react";

import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { SelectField } from "@/components/ui/SelectField";
import { TextField } from "@/components/ui/TextField";
import { ApiError, apiFetch } from "@/lib/api";

interface Claim {
  id: string;
  invoice_id: string;
  student_name: string;
  submitted_by_name: string;
  amount_claimed_paise: number;
  method: string;
  reference_id: string | null;
  submitted_at: string;
  status: string;
}

interface Invoice {
  id: string;
  student_name: string;
  period_start: string;
  period_end: string;
  amount_payable_paise: number;
  paid_paise: number;
  outstanding_paise: number;
  due_date: string;
  status: string;
  has_pending_claim: boolean;
}

interface Student {
  id: string;
  full_name: string;
  grade: string;
}

const rupees = (paise: number) =>
  `₹${(paise / 100).toLocaleString("en-IN", { minimumFractionDigits: 2 })}`;

const dateLabel = (iso: string) =>
  new Date(iso).toLocaleDateString("en-IN", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });

const STATUS_STYLE: Record<string, string> = {
  paid: "bg-success-50 text-success-700",
  pending: "bg-warning-50 text-warning-700",
  partial: "bg-warning-50 text-warning-700",
  overdue: "bg-danger-50 text-danger-700",
};

function firstOfMonth(): string {
  const d = new Date();
  return new Date(d.getFullYear(), d.getMonth(), 1).toISOString().slice(0, 10);
}
function lastOfMonth(): string {
  const d = new Date();
  return new Date(d.getFullYear(), d.getMonth() + 1, 0).toISOString().slice(0, 10);
}

export default function AdminPaymentsPage() {
  const [claims, setClaims] = useState<Claim[] | null>(null);
  const [invoices, setInvoices] = useState<Invoice[] | null>(null);
  const [students, setStudents] = useState<Student[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);

  const [rejecting, setRejecting] = useState<Claim | null>(null);
  const [reason, setReason] = useState("");

  const [raising, setRaising] = useState(false);
  const [invForm, setInvForm] = useState({
    student_id: "",
    amount_rupees: "",
    period_start: firstOfMonth(),
    period_end: lastOfMonth(),
    due_date: lastOfMonth(),
  });

  const load = useCallback(() => {
    apiFetch<Claim[]>("/payments/claims")
      .then(setClaims)
      .catch((e) =>
        setError(e instanceof ApiError ? e.message : "Could not load claims."),
      );
    apiFetch<Invoice[]>("/payments/invoices").then(setInvoices).catch(() => {});
    apiFetch<Student[]>("/admin/students").then(setStudents).catch(() => {});
  }, []);

  useEffect(load, [load]);

  async function verify(claim: Claim) {
    setBusyId(claim.id);
    setError(null);
    setNotice(null);
    try {
      const res = await apiFetch<{
        invoice_status: string;
        receipt_emailed: boolean;
        email_note?: string;
      }>(`/payments/claims/${claim.id}/verify`, { method: "POST", body: {} });

      setNotice(
        res.receipt_emailed
          ? `Payment confirmed. A receipt was emailed to ${claim.student_name}'s parent.`
          : `Payment confirmed. Receipt NOT emailed — ${res.email_note ?? "email is not set up."}`,
      );
      load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not verify.");
    } finally {
      setBusyId(null);
    }
  }

  async function submitReject(e: React.FormEvent) {
    e.preventDefault();
    if (!rejecting) return;
    setBusyId(rejecting.id);
    try {
      await apiFetch(`/payments/claims/${rejecting.id}/reject`, {
        method: "POST",
        body: { reason },
      });
      setRejecting(null);
      setReason("");
      setNotice("Claim rejected. The parent can submit a corrected one.");
      load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not reject.");
    } finally {
      setBusyId(null);
    }
  }

  async function raiseInvoice(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      await apiFetch("/payments/invoices", {
        method: "POST",
        body: {
          student_id: invForm.student_id,
          amount_rupees: Number(invForm.amount_rupees),
          period_start: invForm.period_start,
          period_end: invForm.period_end,
          due_date: invForm.due_date,
        },
      });
      setRaising(false);
      setInvForm((f) => ({ ...f, student_id: "", amount_rupees: "" }));
      setNotice("Fee raised. The parent can now see and pay it.");
      load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not raise the fee.");
    }
  }

  return (
    <div className="mx-auto max-w-5xl">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-navy-900">
            Fees
          </h1>
          <p className="mt-1 text-sm text-ink-500">
            Check each payment against your bank before confirming. A parent&apos;s
            note is a claim, not proof.
          </p>
        </div>
        <Button onClick={() => setRaising(true)} disabled={students.length === 0}>
          Raise a fee
        </Button>
      </header>

      {error && (
        <div
          role="alert"
          className="mt-6 rounded-xl border border-danger-500/25 bg-danger-50 px-4 py-3.5 text-sm text-danger-700"
        >
          {error}
        </div>
      )}
      {notice && (
        <div className="mt-6 rounded-xl border border-success-500/30 bg-success-50 px-4 py-3.5 text-sm text-success-700">
          {notice}
        </div>
      )}

      {/* ---------- Awaiting verification ---------- */}
      <section className="mt-8">
        <h2 className="text-sm font-semibold uppercase tracking-wider text-ink-500">
          Awaiting your confirmation
          {claims && claims.length > 0 && (
            <span className="ml-2 rounded-full bg-warning-500/15 px-2 py-0.5 text-[11px] text-warning-700">
              {claims.length}
            </span>
          )}
        </h2>

        {!claims && (
          <div className="mt-4 h-24 animate-pulse rounded-xl border border-ink-200 bg-white" />
        )}

        {claims?.length === 0 && (
          <p className="mt-4 rounded-xl border border-dashed border-ink-300 bg-white px-6 py-10 text-center text-sm text-ink-500">
            Nothing waiting. Payment notes from parents appear here.
          </p>
        )}

        <div className="mt-4 space-y-3">
          {claims?.map((c) => (
            <div
              key={c.id}
              className="rounded-xl border border-warning-500/40 bg-warning-50 p-5"
            >
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="font-semibold text-navy-900">{c.student_name}</p>
                  <p className="mt-0.5 text-sm text-ink-600">
                    Submitted by {c.submitted_by_name} · {dateLabel(c.submitted_at)}
                  </p>
                  <p className="mt-1 text-sm text-ink-600">
                    Reference:{" "}
                    <span className="font-medium text-ink-900">
                      {c.reference_id ?? "not given"}
                    </span>
                  </p>
                </div>
                <p className="text-xl font-semibold text-navy-900 tabular-nums">
                  {rupees(c.amount_claimed_paise)}
                </p>
              </div>

              <div className="mt-4 flex flex-col gap-2 sm:flex-row">
                <Button
                  className="flex-1"
                  loading={busyId === c.id}
                  onClick={() => verify(c)}
                >
                  Confirm payment received
                </Button>
                <Button
                  variant="secondary"
                  className="flex-1"
                  onClick={() => setRejecting(c)}
                  disabled={busyId === c.id}
                >
                  Reject
                </Button>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* ---------- All fees ---------- */}
      <section className="mt-10">
        <h2 className="text-sm font-semibold uppercase tracking-wider text-ink-500">
          All fees
        </h2>

        {invoices?.length === 0 && (
          <p className="mt-4 rounded-xl border border-dashed border-ink-300 bg-white px-6 py-10 text-center text-sm text-ink-500">
            No fees raised yet.
          </p>
        )}

        {invoices && invoices.length > 0 && (
          <div className="mt-4 overflow-x-auto rounded-xl border border-ink-200 bg-white shadow-[var(--shadow-card)]">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-ink-200 bg-ink-50">
                <tr className="text-xs uppercase tracking-wider text-ink-500">
                  <th className="px-5 py-3 font-semibold">Student</th>
                  <th className="hidden px-5 py-3 font-semibold sm:table-cell">Due</th>
                  <th className="px-5 py-3 text-right font-semibold">Outstanding</th>
                  <th className="px-5 py-3 text-right font-semibold">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-ink-200">
                {invoices.map((i) => (
                  <tr key={i.id} className="transition-colors hover:bg-ink-50">
                    <td className="px-5 py-4 font-medium text-ink-900">
                      {i.student_name}
                    </td>
                    <td className="hidden px-5 py-4 text-ink-600 sm:table-cell">
                      {dateLabel(i.due_date)}
                    </td>
                    <td className="px-5 py-4 text-right tabular-nums text-ink-900">
                      {rupees(i.outstanding_paise)}
                    </td>
                    <td className="px-5 py-4 text-right">
                      <span
                        className={`rounded px-2 py-0.5 text-[11px] font-medium ${
                          STATUS_STYLE[i.status] ?? "bg-ink-100 text-ink-600"
                        }`}
                      >
                        {i.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {/* ---------- Raise a fee ---------- */}
      <Modal
        open={raising}
        title="Raise a fee"
        description="The parent sees this immediately and can pay by UPI."
        onClose={() => setRaising(false)}
      >
        <form onSubmit={raiseInvoice} className="space-y-4" noValidate>
          <SelectField
            label="Student"
            value={invForm.student_id}
            onChange={(e) =>
              setInvForm((f) => ({ ...f, student_id: e.target.value }))
            }
            options={students.map((s) => ({
              value: s.id,
              label: `${s.full_name} · Grade ${s.grade}`,
            }))}
            placeholder="Choose a student"
            required
          />
          <TextField
            label="Amount (₹)"
            type="number"
            step="1"
            min="1"
            value={invForm.amount_rupees}
            onChange={(e) =>
              setInvForm((f) => ({ ...f, amount_rupees: e.target.value }))
            }
            placeholder="2500"
            required
          />
          <div className="grid gap-4 sm:grid-cols-2">
            <TextField
              label="Period from"
              type="date"
              value={invForm.period_start}
              onChange={(e) =>
                setInvForm((f) => ({ ...f, period_start: e.target.value }))
              }
              required
            />
            <TextField
              label="Period to"
              type="date"
              value={invForm.period_end}
              onChange={(e) =>
                setInvForm((f) => ({ ...f, period_end: e.target.value }))
              }
              required
            />
          </div>
          <TextField
            label="Due date"
            type="date"
            value={invForm.due_date}
            onChange={(e) => setInvForm((f) => ({ ...f, due_date: e.target.value }))}
            required
          />

          <div className="flex gap-3 pt-1">
            <Button
              type="button"
              variant="secondary"
              className="flex-1"
              onClick={() => setRaising(false)}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              className="flex-1"
              disabled={!invForm.student_id || !invForm.amount_rupees}
            >
              Raise fee
            </Button>
          </div>
        </form>
      </Modal>

      {/* ---------- Reject ---------- */}
      <Modal
        open={rejecting !== null}
        title="Reject this payment note"
        description="The parent will see your reason and can submit a corrected one."
        onClose={() => setRejecting(null)}
      >
        <form onSubmit={submitReject} className="space-y-4" noValidate>
          <TextField
            label="Reason"
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            placeholder="e.g. No matching payment found in the bank statement"
            required
          />
          <div className="flex gap-3 pt-1">
            <Button
              type="button"
              variant="secondary"
              className="flex-1"
              onClick={() => setRejecting(null)}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              variant="danger"
              className="flex-1"
              disabled={reason.trim().length < 3}
            >
              Reject
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
