"use client";

import { useEffect, useState } from "react";

import { StatCard } from "@/components/app/StatCard";
import { ApiError, apiFetch } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";

interface Counts {
  students_total: number;
  students_suspended: number;
  parents_total: number;
  tutors_total: number;
  batches_active: number;
  batches_at_capacity: number;
  classes_today: number;
  classes_upcoming_7d: number;
  attendance_discrepancies: number;
  payments_pending_review: number;
  invoices_overdue: number;
  questions_pending_review: number;
}

interface SetupTask {
  key: string;
  label: string;
  done: boolean;
  hint: string | null;
}

interface Overview {
  counts: Counts;
  setup: SetupTask[];
  is_empty: boolean;
}

const ICONS = {
  students: <path d="M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8Zm-8 8a8 8 0 0 1 16 0" />,
  parents: <path d="M8 11a3 3 0 1 0 0-6 3 3 0 0 0 0 6Zm8 0a3 3 0 1 0 0-6 3 3 0 0 0 0 6ZM2 20a6 6 0 0 1 12 0m-2-9a6 6 0 0 1 10 9" />,
  tutors: <path d="M12 3 2 8l10 5 10-5-10-5Zm0 9.5L5 9v4.5c0 2 3.1 3.5 7 3.5s7-1.5 7-3.5V9" />,
  batches: <path d="M4 6h16M4 12h16M4 18h16" />,
  calendar: <path d="M8 2v4m8-4v4M3 9h18M5 5h14a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2Z" />,
  alert: <path d="M12 9v4m0 4h.01M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0Z" />,
  rupee: <path d="M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18Zm3-12H10.5a2 2 0 0 0 0 4h3a2 2 0 0 1 0 4H9" />,
  review: <path d="M9 11l3 3 7-7M20 12v7a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V5a1 1 0 0 1 1-1h9" />,
};

function SkeletonCard() {
  return (
    <div className="h-[132px] animate-pulse rounded-xl border border-ink-200 bg-white p-5">
      <div className="h-9 w-9 rounded-lg bg-ink-100" />
      <div className="mt-4 h-8 w-14 rounded bg-ink-100" />
      <div className="mt-2 h-3.5 w-24 rounded bg-ink-100" />
    </div>
  );
}

export default function AdminDashboard() {
  const { user } = useAuth();
  const [data, setData] = useState<Overview | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    apiFetch<Overview>("/admin/overview")
      .then((d) => {
        if (!cancelled) setData(d);
      })
      .catch((e) => {
        if (!cancelled) {
          setError(
            e instanceof ApiError ? e.message : "Could not load your dashboard.",
          );
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const firstName = user?.full_name.split(" ")[0] ?? "";
  const completed = data?.setup.filter((t) => t.done).length ?? 0;
  const total = data?.setup.length ?? 0;

  return (
    <div className="mx-auto max-w-6xl">
      <header>
        <h1 className="text-2xl font-semibold tracking-tight text-navy-900">
          Welcome back{firstName && `, ${firstName}`}
        </h1>
        <p className="mt-1 text-sm text-ink-500">
          Everything happening across SS Tuitions right now.
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

      {/* ---------- Loading ---------- */}
      {!data && !error && (
        <div className="mt-8 grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
          {Array.from({ length: 8 }).map((_, i) => (
            <SkeletonCard key={i} />
          ))}
        </div>
      )}

      {data && (
        <>
          {/* ---------- Setup checklist, while the platform is new ---------- */}
          {completed < total && (
            <section className="mt-8 animate-[var(--animate-fade-up)] rounded-xl border border-navy-200 bg-white p-6 shadow-[var(--shadow-card)]">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <h2 className="font-semibold text-navy-900">Finish setting up</h2>
                  <p className="mt-1 text-sm text-ink-500">
                    {data.is_empty
                      ? "Your platform is ready. These steps bring it to life."
                      : "A few things left before everything works end to end."}
                  </p>
                </div>
                <span className="text-sm font-medium text-ink-600 tabular-nums">
                  {completed} of {total}
                </span>
              </div>

              <div
                className="mt-4 h-1.5 w-full overflow-hidden rounded-full bg-ink-100"
                role="progressbar"
                aria-valuenow={completed}
                aria-valuemin={0}
                aria-valuemax={total}
                aria-label="Setup progress"
              >
                <div
                  className="h-full rounded-full bg-gold-500 transition-all duration-500 ease-[var(--ease-out-soft)]"
                  style={{ width: `${total ? (completed / total) * 100 : 0}%` }}
                />
              </div>

              <ul className="mt-5 space-y-2.5">
                {data.setup.map((task) => (
                  <li key={task.key} className="flex items-start gap-3">
                    <span
                      className={[
                        "mt-px flex h-5 w-5 shrink-0 items-center justify-center rounded-full border",
                        task.done
                          ? "border-success-500 bg-success-500 text-white"
                          : "border-ink-300",
                      ].join(" ")}
                      aria-hidden="true"
                    >
                      {task.done && (
                        <svg className="h-3 w-3" viewBox="0 0 20 20" fill="currentColor">
                          <path
                            fillRule="evenodd"
                            d="M16.7 5.3a1 1 0 010 1.4l-7.5 7.5a1 1 0 01-1.4 0L3.3 9.7a1 1 0 111.4-1.4l3.8 3.8 6.8-6.8a1 1 0 011.4 0z"
                            clipRule="evenodd"
                          />
                        </svg>
                      )}
                    </span>
                    <div className="min-w-0">
                      <p
                        className={[
                          "text-sm",
                          task.done ? "text-ink-400 line-through" : "font-medium text-ink-800",
                        ].join(" ")}
                      >
                        {task.label}
                      </p>
                      {!task.done && task.hint && (
                        <p className="mt-0.5 text-xs text-ink-500">{task.hint}</p>
                      )}
                    </div>
                  </li>
                ))}
              </ul>
            </section>
          )}

          {/* ---------- Needs your attention ---------- */}
          <section className="mt-8">
            <h2 className="text-sm font-semibold uppercase tracking-wider text-ink-500">
              Needs your attention
            </h2>
            <div className="mt-4 grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
              <StatCard
                label="Payments to verify"
                value={data.counts.payments_pending_review}
                icon={ICONS.rupee}
                attention
                hint="A parent's upload is only a claim until you confirm it."
              />
              <StatCard
                label="Attendance disputes"
                value={data.counts.attendance_discrepancies}
                icon={ICONS.alert}
                attention
                hint="Student and tutor marked differently."
              />
              <StatCard
                label="Overdue fees"
                value={data.counts.invoices_overdue}
                icon={ICONS.rupee}
                attention
              />
              <StatCard
                label="Questions to review"
                value={data.counts.questions_pending_review}
                icon={ICONS.review}
                attention
                hint="AI-generated questions stay hidden until approved."
              />
            </div>
          </section>

          {/* ---------- People ---------- */}
          <section className="mt-8">
            <h2 className="text-sm font-semibold uppercase tracking-wider text-ink-500">
              People
            </h2>
            <div className="mt-4 grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
              <StatCard
                label="Students"
                value={data.counts.students_total}
                icon={ICONS.students}
                href="/admin/students"
                hint={
                  data.counts.students_suspended > 0
                    ? `${data.counts.students_suspended} suspended`
                    : undefined
                }
              />
              <StatCard
                label="Parents"
                value={data.counts.parents_total}
                icon={ICONS.parents}
                href="/admin/parents"
              />
              <StatCard
                label="Tutors"
                value={data.counts.tutors_total}
                icon={ICONS.tutors}
                href="/admin/tutors"
              />
              <StatCard
                label="Active batches"
                value={data.counts.batches_active}
                icon={ICONS.batches}
                href="/admin/batches"
                hint={
                  data.counts.batches_at_capacity > 0
                    ? `${data.counts.batches_at_capacity} full`
                    : undefined
                }
              />
            </div>
          </section>

          {/* ---------- Classes ---------- */}
          <section className="mt-8">
            <h2 className="text-sm font-semibold uppercase tracking-wider text-ink-500">
              Classes
            </h2>
            <div className="mt-4 grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
              <StatCard
                label="Today"
                value={data.counts.classes_today}
                icon={ICONS.calendar}
                href="/admin/classes"
              />
              <StatCard
                label="Next 7 days"
                value={data.counts.classes_upcoming_7d}
                icon={ICONS.calendar}
                href="/admin/classes"
              />
            </div>
          </section>

          <p className="mt-10 text-xs text-ink-400">
            All figures are live counts from your database. Nothing here is
            sample or estimated data.
          </p>
        </>
      )}
    </div>
  );
}
