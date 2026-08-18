"use client";

import Image from "next/image";
import { useCallback, useEffect, useState } from "react";

import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { TextField } from "@/components/ui/TextField";
import { ApiError, apiFetch } from "@/lib/api";

interface PaymentDetails {
  configured: boolean;
  upi_id: string | null;
  payee_name: string | null;
  phone_number: string | null;
  bank_name: string | null;
  account_number: string | null;
  ifsc: string | null;
  qr_image_url: string | null;
  instructions: string | null;
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

const rupees = (paise: number) =>
  `₹${(paise / 100).toLocaleString("en-IN", { minimumFractionDigits: 2 })}`;

const dateLabel = (iso: string) =>
  new Date(`${iso}T00:00:00`).toLocaleDateString("en-IN", {
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

export default function ParentFeesPage() {
  const [details, setDetails] = useState<PaymentDetails | null>(null);
  const [invoices, setInvoices] = useState<Invoice[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [qrFailed, setQrFailed] = useState(false);
  const [payFor, setPayFor] = useState<Invoice | null>(null);
  const [reference, setReference] = useState("");
  const [amount, setAmount] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [done, setDone] = useState<string | null>(null);

  const load = useCallback(() => {
    apiFetch<PaymentDetails>("/payments/details").then(setDetails).catch(() => {});
    apiFetch<Invoice[]>("/payments/invoices")
      .then(setInvoices)
      .catch((e) =>
        setError(e instanceof ApiError ? e.message : "Could not load fees."),
      );
  }, []);

  useEffect(load, [load]);

  function openPay(inv: Invoice) {
    setPayFor(inv);
    setAmount((inv.outstanding_paise / 100).toString());
    setReference("");
  }

  async function submitClaim(e: React.FormEvent) {
    e.preventDefault();
    if (!payFor) return;
    setSubmitting(true);
    setError(null);
    try {
      const res = await apiFetch<{ message: string }>("/payments/claims", {
        method: "POST",
        body: {
          invoice_id: payFor.id,
          amount_rupees: Number(amount),
          method: "upi",
          reference_id: reference.trim() || null,
        },
      });
      setPayFor(null);
      setDone(res.message);
      load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not submit.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="mx-auto max-w-3xl">
      <header>
        <h1 className="text-2xl font-semibold tracking-tight text-navy-900">Fees</h1>
        <p className="mt-1 text-sm text-ink-500">
          Pay by UPI, then tell us — we confirm and email you a receipt.
        </p>
      </header>

      {error && (
        <div
          role="alert"
          className="mt-6 rounded-xl border border-danger-500/25 bg-danger-50 px-4 py-3.5 text-sm text-danger-700"
        >
          {error}
        </div>
      )}

      {done && (
        <div className="mt-6 rounded-xl border border-success-500/30 bg-success-50 px-4 py-3.5 text-sm text-success-700">
          {done}
        </div>
      )}

      {/* ---------- Invoices ---------- */}
      <section className="mt-8">
        <h2 className="text-sm font-semibold uppercase tracking-wider text-ink-500">
          Your fees
        </h2>

        {!invoices && (
          <div className="mt-4 h-24 animate-pulse rounded-xl border border-ink-200 bg-white" />
        )}

        {invoices?.length === 0 && (
          <div className="mt-4 rounded-xl border border-dashed border-ink-300 bg-white px-6 py-12 text-center">
            <p className="font-medium text-navy-900">Nothing due</p>
            <p className="mt-1 text-sm text-ink-500">
              You have no fees to pay right now.
            </p>
          </div>
        )}

        <div className="mt-4 space-y-3">
          {invoices?.map((inv) => (
            <div
              key={inv.id}
              className="rounded-xl border border-ink-200 bg-white p-5 shadow-[var(--shadow-card)]"
            >
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="font-semibold text-navy-900">{inv.student_name}</p>
                  <p className="mt-0.5 text-sm text-ink-500">
                    {dateLabel(inv.period_start)} – {dateLabel(inv.period_end)}
                  </p>
                  <p className="mt-1 text-xs text-ink-500">
                    Due {dateLabel(inv.due_date)}
                  </p>
                </div>
                <div className="text-right">
                  <p className="text-xl font-semibold text-navy-900 tabular-nums">
                    {rupees(inv.outstanding_paise)}
                  </p>
                  <span
                    className={`mt-1 inline-block rounded px-2 py-0.5 text-[11px] font-medium ${
                      STATUS_STYLE[inv.status] ?? "bg-ink-100 text-ink-600"
                    }`}
                  >
                    {inv.status}
                  </span>
                </div>
              </div>

              {inv.has_pending_claim ? (
                <p className="mt-4 rounded-lg border border-warning-500/25 bg-warning-50 px-3.5 py-2.5 text-sm text-warning-700">
                  We have your payment note and are confirming it. You will get
                  an email once it is verified.
                </p>
              ) : (
                inv.outstanding_paise > 0 && (
                  <Button className="mt-4 w-full" onClick={() => openPay(inv)}>
                    I have paid
                  </Button>
                )
              )}
            </div>
          ))}
        </div>
      </section>

      {/* ---------- How to pay ---------- */}
      <section className="mt-10">
        <h2 className="text-sm font-semibold uppercase tracking-wider text-ink-500">
          How to pay
        </h2>

        {details && !details.configured && (
          <div className="mt-4 rounded-xl border border-dashed border-ink-300 bg-white px-6 py-10 text-center text-sm text-ink-500">
            Payment details have not been set up yet. Please contact SS Tuitions.
          </div>
        )}

        {details?.configured && (
          <div className="mt-4 rounded-xl border border-ink-200 bg-white p-6 shadow-[var(--shadow-card)]">
            {/* If the QR file is missing the image is hidden entirely rather
                than left as a broken icon — the UPI id below is enough to pay
                with, so a failed image must not block payment. */}
            {details.qr_image_url && !qrFailed && (
              <div className="flex flex-col items-center">
                <Image
                  src={details.qr_image_url}
                  alt="UPI QR code for SS Tuitions"
                  width={220}
                  height={220}
                  className="rounded-lg border border-ink-200"
                  unoptimized
                  onError={() => setQrFailed(true)}
                />
                <p className="mt-3 text-sm text-ink-600">
                  Scan with PhonePe, Google Pay or Paytm
                </p>
              </div>
            )}

            <dl className="mt-6 space-y-2.5 text-sm">
              {details.upi_id && (
                <div className="flex justify-between gap-4">
                  <dt className="text-ink-500">UPI ID</dt>
                  <dd className="font-medium text-ink-900">{details.upi_id}</dd>
                </div>
              )}
              {details.phone_number && (
                <div className="flex justify-between gap-4">
                  <dt className="text-ink-500">Phone (PhonePe / GPay / Paytm)</dt>
                  <dd className="font-medium text-ink-900">
                    {details.phone_number}
                  </dd>
                </div>
              )}
              {details.payee_name && (
                <div className="flex justify-between gap-4">
                  <dt className="text-ink-500">Account holder</dt>
                  <dd className="font-medium text-ink-900">{details.payee_name}</dd>
                </div>
              )}
              {details.bank_name && (
                <div className="flex justify-between gap-4">
                  <dt className="text-ink-500">Bank</dt>
                  <dd className="font-medium text-ink-900">{details.bank_name}</dd>
                </div>
              )}
              {details.account_number && (
                <div className="flex justify-between gap-4">
                  <dt className="text-ink-500">Account number</dt>
                  <dd className="font-medium text-ink-900 tabular-nums">
                    {details.account_number}
                  </dd>
                </div>
              )}
              {details.ifsc && (
                <div className="flex justify-between gap-4">
                  <dt className="text-ink-500">IFSC</dt>
                  <dd className="font-medium text-ink-900">{details.ifsc}</dd>
                </div>
              )}
            </dl>

            {details.instructions && (
              <p className="mt-5 rounded-lg bg-ink-50 px-4 py-3 text-sm leading-relaxed text-ink-600">
                {details.instructions}
              </p>
            )}
          </div>
        )}
      </section>

      {/* ---------- I have paid ---------- */}
      <Modal
        open={payFor !== null}
        title="Tell us you have paid"
        description="We will confirm it and email you a receipt."
        onClose={() => setPayFor(null)}
      >
        <form onSubmit={submitClaim} className="space-y-4" noValidate>
          <TextField
            label="Amount paid (₹)"
            type="number"
            step="0.01"
            min="1"
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
            required
            disabled={submitting}
          />
          <TextField
            label="Transaction reference"
            value={reference}
            onChange={(e) => setReference(e.target.value)}
            placeholder="e.g. 402312345678"
            hint="The UPI reference number from your payment app. It helps us match your payment quickly."
            disabled={submitting}
          />

          <p className="rounded-lg bg-ink-50 px-3.5 py-3 text-xs leading-relaxed text-ink-500">
            This tells SS Tuitions you have paid. Your fee is marked paid only
            after we check it against our bank records.
          </p>

          <div className="flex gap-3 pt-1">
            <Button
              type="button"
              variant="secondary"
              className="flex-1"
              onClick={() => setPayFor(null)}
              disabled={submitting}
            >
              Cancel
            </Button>
            <Button type="submit" className="flex-1" loading={submitting}>
              Submit
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
