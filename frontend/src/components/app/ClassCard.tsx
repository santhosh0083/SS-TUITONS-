"use client";

export interface ClassSession {
  id: string;
  batch_code: string;
  subject: string;
  student_name: string;
  tutor_name: string;
  scheduled_date: string;
  scheduled_start: string;
  scheduled_end: string;
  status: string;
  integration_status: string;
  meeting_url: string | null;
  can_join: boolean;
  join_hint: string | null;
}

function formatTime(t: string): string {
  const [h, m] = t.split(":").map(Number);
  const period = h >= 12 ? "PM" : "AM";
  const hour = h % 12 === 0 ? 12 : h % 12;
  return `${hour}:${String(m).padStart(2, "0")} ${period}`;
}

function dayLabel(iso: string): string {
  const d = new Date(`${iso}T00:00:00`);
  const today = new Date();
  const tomorrow = new Date(today);
  tomorrow.setDate(today.getDate() + 1);

  if (d.toDateString() === today.toDateString()) return "Today";
  if (d.toDateString() === tomorrow.toDateString()) return "Tomorrow";
  return d.toLocaleDateString("en-IN", {
    weekday: "short",
    day: "numeric",
    month: "short",
  });
}

/**
 * A scheduled class.
 *
 * `who` decides which name is shown: a parent sees the tutor, a tutor sees the
 * student. Neither ever receives the other's contact details — the API does
 * not return them.
 */
export function ClassCard({
  session,
  who,
}: {
  session: ClassSession;
  who: "tutor" | "student";
}) {
  const isToday = dayLabel(session.scheduled_date) === "Today";
  const counterpartLabel = who === "tutor" ? "Tutor" : "Student";
  const counterpartName =
    who === "tutor" ? session.tutor_name : session.student_name;

  return (
    <article
      className={[
        "rounded-xl border bg-white p-5 transition-all duration-200 ease-[var(--ease-out-soft)]",
        session.can_join
          ? "border-success-500/40 shadow-[var(--shadow-card)]"
          : "border-ink-200 shadow-[var(--shadow-card)]",
      ].join(" ")}
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <h3 className="font-semibold text-navy-900">{session.subject}</h3>
            {isToday && (
              <span className="rounded-full bg-gold-100 px-2 py-0.5 text-[11px] font-semibold text-gold-800">
                Today
              </span>
            )}
          </div>
          <p className="mt-1 text-sm text-ink-600">
            <span className="text-ink-500">{counterpartLabel}:</span>{" "}
            {counterpartName}
          </p>
        </div>

        <div className="text-right">
          <p className="text-sm font-medium text-navy-900">
            {dayLabel(session.scheduled_date)}
          </p>
          <p className="text-sm text-ink-600 tabular-nums">
            {formatTime(session.scheduled_start)} –{" "}
            {formatTime(session.scheduled_end)}
          </p>
        </div>
      </div>

      <div className="mt-5">
        {session.can_join && session.meeting_url ? (
          <a
            href={session.meeting_url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex h-11 w-full items-center justify-center gap-2 rounded-lg bg-success-500 px-5 text-sm font-semibold text-white transition-all duration-150 hover:-translate-y-px hover:bg-success-700"
          >
            <svg
              className="h-4 w-4"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.8"
              aria-hidden="true"
            >
              <path d="m23 7-7 5 7 5V7Z" />
              <rect x="1" y="5" width="15" height="14" rx="2" />
            </svg>
            Join class
          </a>
        ) : (
          <div className="rounded-lg border border-ink-200 bg-ink-50 px-4 py-3 text-center">
            <p className="text-sm text-ink-500">
              {session.join_hint ?? "Not available yet."}
            </p>
          </div>
        )}
      </div>
    </article>
  );
}
