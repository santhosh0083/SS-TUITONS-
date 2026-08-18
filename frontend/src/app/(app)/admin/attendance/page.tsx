"use client";

import { useCallback, useEffect, useState } from "react";

import { Button } from "@/components/ui/Button";
import { ApiError, apiFetch } from "@/lib/api";

interface Discrepancy {
  attendance_id: string;
  student_name: string;
  scheduled_date: string;
  student_marked: string | null;
  tutor_marked: string | null;
}

const dateLabel = (iso: string) =>
  new Date(`${iso}T00:00:00`).toLocaleDateString("en-IN", {
    weekday: "short",
    day: "numeric",
    month: "short",
    year: "numeric",
  });

export default function AdminAttendancePage() {
  const [rows, setRows] = useState<Discrepancy[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);

  const load = useCallback(() => {
    apiFetch<Discrepancy[]>("/attendance/discrepancies")
      .then(setRows)
      .catch((e) =>
        setError(e instanceof ApiError ? e.message : "Could not load."),
      );
  }, []);

  useEffect(load, [load]);

  async function resolve(id: string, final: string, who: string) {
    setBusyId(id);
    setError(null);
    try {
      await apiFetch(`/attendance/discrepancies/${id}/resolve`, {
        method: "POST",
        body: { final },
      });
      setNotice(`Recorded as "${final}" — you accepted the ${who} mark.`);
      load();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Could not resolve.");
    } finally {
      setBusyId(null);
    }
  }

  return (
    <div className="mx-auto max-w-3xl">
      <header>
        <h1 className="text-2xl font-semibold tracking-tight text-navy-900">
          Attendance disputes
        </h1>
        <p className="mt-1 text-sm text-ink-500">
          Where a student and tutor marked the same class differently. Neither
          overwrites the other — you decide.
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
      {notice && (
        <div className="mt-6 rounded-xl border border-success-500/30 bg-success-50 px-4 py-3.5 text-sm text-success-700">
          {notice}
        </div>
      )}

      {!rows && (
        <div className="mt-8 h-24 animate-pulse rounded-xl border border-ink-200 bg-white" />
      )}

      {rows?.length === 0 && (
        <div className="mt-8 rounded-xl border border-dashed border-ink-300 bg-white px-6 py-14 text-center">
          <span className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-success-50">
            <svg
              className="h-6 w-6 text-success-500"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.5"
              aria-hidden="true"
            >
              <path d="m9 11 3 3 7-7M20 12v7a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V5a1 1 0 0 1 1-1h9" />
            </svg>
          </span>
          <h2 className="mt-4 font-semibold text-navy-900">Nothing disputed</h2>
          <p className="mx-auto mt-1.5 max-w-sm text-sm text-ink-500">
            Student and tutor marks agree on every class so far.
          </p>
        </div>
      )}

      <div className="mt-8 space-y-4">
        {rows?.map((d) => (
          <article
            key={d.attendance_id}
            className="rounded-xl border border-warning-500/40 bg-warning-50 p-5"
          >
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <h3 className="font-semibold text-navy-900">{d.student_name}</h3>
                <p className="mt-0.5 text-sm text-ink-600">
                  {dateLabel(d.scheduled_date)}
                </p>
              </div>
            </div>

            <div className="mt-4 grid grid-cols-2 gap-3">
              <div className="rounded-lg border border-ink-200 bg-white p-3 text-center">
                <p className="text-xs uppercase tracking-wider text-ink-500">
                  Student said
                </p>
                <p className="mt-1 font-semibold text-navy-900">
                  {d.student_marked ?? "—"}
                </p>
              </div>
              <div className="rounded-lg border border-ink-200 bg-white p-3 text-center">
                <p className="text-xs uppercase tracking-wider text-ink-500">
                  Tutor said
                </p>
                <p className="mt-1 font-semibold text-navy-900">
                  {d.tutor_marked ?? "—"}
                </p>
              </div>
            </div>

            <div className="mt-4 flex flex-col gap-2 sm:flex-row">
              {d.student_marked && (
                <Button
                  variant="secondary"
                  className="flex-1"
                  loading={busyId === d.attendance_id}
                  onClick={() =>
                    resolve(d.attendance_id, d.student_marked!, "student")
                  }
                >
                  Accept student ({d.student_marked})
                </Button>
              )}
              {d.tutor_marked && (
                <Button
                  className="flex-1"
                  loading={busyId === d.attendance_id}
                  onClick={() => resolve(d.attendance_id, d.tutor_marked!, "tutor")}
                >
                  Accept tutor ({d.tutor_marked})
                </Button>
              )}
            </div>
          </article>
        ))}
      </div>

      {rows && rows.length > 0 && (
        <p className="mt-6 text-xs text-ink-400">
          Your decision is written to the audit log, which cannot be edited or
          deleted.
        </p>
      )}
    </div>
  );
}
