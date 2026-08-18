"use client";

import { useCallback, useEffect, useState } from "react";

import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { TextField } from "@/components/ui/TextField";
import { ApiError, apiFetch } from "@/lib/api";

interface ClassSession {
  id: string;
  subject: string;
  student_name: string;
  scheduled_date: string;
  scheduled_start: string;
  scheduled_end: string;
  status: string;
}

interface RosterEntry {
  student_id: string;
  student_name: string;
  student_marked: string | null;
  tutor_marked: string | null;
  final_status: string | null;
  has_discrepancy: boolean;
}

type Mark = "present" | "absent" | "late" | "excused";

const MARKS: { value: Mark; label: string; style: string }[] = [
  { value: "present", label: "Present", style: "bg-success-500 text-white border-success-500" },
  { value: "late", label: "Late", style: "bg-warning-500 text-white border-warning-500" },
  { value: "absent", label: "Absent", style: "bg-danger-500 text-white border-danger-500" },
  { value: "excused", label: "Excused", style: "bg-ink-500 text-white border-ink-500" },
];

const time = (t: string) => {
  const [h, m] = t.split(":").map(Number);
  const p = h >= 12 ? "PM" : "AM";
  return `${h % 12 === 0 ? 12 : h % 12}:${String(m).padStart(2, "0")} ${p}`;
};

const dayLabel = (iso: string) => {
  const d = new Date(`${iso}T00:00:00`);
  const today = new Date();
  if (d.toDateString() === today.toDateString()) return "Today";
  return d.toLocaleDateString("en-IN", { weekday: "short", day: "numeric", month: "short" });
};

/** Combine a class date and time into an ISO timestamp for the report form. */
function isoAt(dateIso: string, timeStr: string): string {
  return new Date(`${dateIso}T${timeStr}`).toISOString().slice(0, 16);
}

export default function TutorAttendancePage() {
  const [classes, setClasses] = useState<ClassSession[] | null>(null);
  const [active, setActive] = useState<ClassSession | null>(null);
  const [roster, setRoster] = useState<RosterEntry[] | null>(null);
  const [marks, setMarks] = useState<Record<string, Mark>>({});
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const [reportFor, setReportFor] = useState<ClassSession | null>(null);
  const [report, setReport] = useState({
    topics_covered: "",
    actual_start_at: "",
    actual_end_at: "",
    homework_assigned: "",
  });

  const load = useCallback(() => {
    apiFetch<ClassSession[]>("/classes/mine")
      .then(setClasses)
      .catch((e) =>
        setError(e instanceof ApiError ? e.message : "Could not load classes."),
      );
  }, []);

  useEffect(load, [load]);

  const openRoster = useCallback((c: ClassSession) => {
    setActive(c);
    setRoster(null);
    setMarks({});
    setError(null);
    apiFetch<RosterEntry[]>(`/attendance/${c.id}/roster`)
      .then((r) => {
        setRoster(r);
        // Pre-fill with any mark already made, so re-submitting does not wipe it.
        const seeded: Record<string, Mark> = {};
        r.forEach((e) => {
          if (e.tutor_marked) seeded[e.student_id] = e.tutor_marked as Mark;
        });
        setMarks(seeded);
      })
      .catch((e) =>
        setError(e instanceof ApiError ? e.message : "Could not load the roster."),
      );
  }, []);

  async function submitMarks() {
    if (!active) return;
    setBusy(true);
    setError(null);
    try {
      const res = await apiFetch<{ marked: number }>(
        `/attendance/${active.id}/tutor-mark`,
        { method: "POST", body: { marks } },
      );
      setNotice(`Attendance saved for ${res.marked} student(s).`);
      openRoster(active);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Could not save attendance.");
    } finally {
      setBusy(false);
    }
  }

  function openReport(c: ClassSession) {
    setReportFor(c);
    setReport({
      topics_covered: "",
      actual_start_at: isoAt(c.scheduled_date, c.scheduled_start),
      actual_end_at: isoAt(c.scheduled_date, c.scheduled_end),
      homework_assigned: "",
    });
  }

  async function submitReport(e: React.FormEvent) {
    e.preventDefault();
    if (!reportFor) return;
    setBusy(true);
    setError(null);
    try {
      await apiFetch(`/attendance/${reportFor.id}/report`, {
        method: "POST",
        body: {
          topics_covered: report.topics_covered,
          actual_start_at: new Date(report.actual_start_at).toISOString(),
          actual_end_at: new Date(report.actual_end_at).toISOString(),
          homework_assigned: report.homework_assigned || null,
        },
      });
      setReportFor(null);
      setNotice("Class report submitted. SS Tuitions can now review it.");
      load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not submit the report.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto max-w-3xl">
      <header>
        <h1 className="text-2xl font-semibold tracking-tight text-navy-900">
          Attendance
        </h1>
        <p className="mt-1 text-sm text-ink-500">
          Mark who attended, then log what you taught.
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

      {!classes && (
        <div className="mt-8 h-32 animate-pulse rounded-xl border border-ink-200 bg-white" />
      )}

      {classes?.length === 0 && (
        <div className="mt-8 rounded-xl border border-dashed border-ink-300 bg-white px-6 py-14 text-center">
          <h2 className="font-semibold text-navy-900">No classes yet</h2>
          <p className="mx-auto mt-1.5 max-w-sm text-sm text-ink-500">
            Once SS Tuitions schedules a class for you, it appears here.
          </p>
        </div>
      )}

      <div className="mt-8 space-y-4">
        {classes?.map((c) => (
          <article
            key={c.id}
            className="rounded-xl border border-ink-200 bg-white p-5 shadow-[var(--shadow-card)]"
          >
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <h3 className="font-semibold text-navy-900">{c.subject}</h3>
                <p className="mt-0.5 text-sm text-ink-600">{c.student_name}</p>
              </div>
              <div className="text-right text-sm">
                <p className="font-medium text-navy-900">
                  {dayLabel(c.scheduled_date)}
                </p>
                <p className="text-ink-600 tabular-nums">
                  {time(c.scheduled_start)} – {time(c.scheduled_end)}
                </p>
              </div>
            </div>

            <div className="mt-4 flex flex-col gap-2 sm:flex-row">
              <Button
                variant="secondary"
                className="flex-1"
                onClick={() => openRoster(c)}
              >
                Mark attendance
              </Button>
              <Button className="flex-1" onClick={() => openReport(c)}>
                Log what I taught
              </Button>
            </div>

            {/* Roster expands inline for the selected class */}
            {active?.id === c.id && (
              <div className="mt-5 border-t border-ink-200 pt-5">
                {!roster && (
                  <div className="h-16 animate-pulse rounded-lg bg-ink-100" />
                )}

                {roster?.map((entry) => (
                  <div key={entry.student_id} className="mb-4 last:mb-0">
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-sm font-medium text-ink-900">
                        {entry.student_name}
                      </span>
                      {entry.student_marked && (
                        <span className="text-xs text-ink-500">
                          student said: {entry.student_marked}
                        </span>
                      )}
                    </div>
                    <div className="mt-2 grid grid-cols-4 gap-1.5">
                      {MARKS.map((m) => {
                        const chosen = marks[entry.student_id] === m.value;
                        return (
                          <button
                            key={m.value}
                            type="button"
                            aria-pressed={chosen}
                            onClick={() =>
                              setMarks((prev) => ({
                                ...prev,
                                [entry.student_id]: m.value,
                              }))
                            }
                            className={[
                              "rounded-lg border px-2 py-2 text-xs font-medium transition-all",
                              chosen
                                ? m.style
                                : "border-ink-300 text-ink-600 hover:bg-ink-50",
                            ].join(" ")}
                          >
                            {m.label}
                          </button>
                        );
                      })}
                    </div>
                    {entry.has_discrepancy && (
                      <p className="mt-1.5 text-xs text-warning-700">
                        You and the student marked this differently. SS Tuitions
                        will decide.
                      </p>
                    )}
                  </div>
                ))}

                {roster && roster.length > 0 && (
                  <Button
                    className="mt-2 w-full"
                    loading={busy}
                    disabled={Object.keys(marks).length === 0}
                    onClick={submitMarks}
                  >
                    Save attendance
                  </Button>
                )}

                {roster?.length === 0 && (
                  <p className="text-sm text-ink-500">
                    No students enrolled in this class yet.
                  </p>
                )}
              </div>
            )}
          </article>
        ))}
      </div>

      {/* ---------- Class report ---------- */}
      <Modal
        open={reportFor !== null}
        title="What did you teach?"
        description="SS Tuitions reviews this and may share it with the parent."
        onClose={() => setReportFor(null)}
      >
        <form onSubmit={submitReport} className="space-y-4" noValidate>
          <div>
            <label
              htmlFor="topics"
              className="mb-1.5 block text-sm font-medium text-ink-700"
            >
              Topics covered
            </label>
            <textarea
              id="topics"
              rows={3}
              value={report.topics_covered}
              onChange={(e) =>
                setReport((r) => ({ ...r, topics_covered: e.target.value }))
              }
              placeholder="e.g. Projectile motion — range and maximum height, worked 4 problems"
              required
              disabled={busy}
              className="w-full rounded-lg border border-ink-300 px-3.5 py-2.5 text-sm text-ink-900 placeholder:text-ink-400 focus:border-navy-500 focus:outline-none focus:ring-2 focus:ring-navy-500/25"
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <TextField
              label="Actually started"
              type="datetime-local"
              value={report.actual_start_at}
              onChange={(e) =>
                setReport((r) => ({ ...r, actual_start_at: e.target.value }))
              }
              required
              disabled={busy}
            />
            <TextField
              label="Actually ended"
              type="datetime-local"
              value={report.actual_end_at}
              onChange={(e) =>
                setReport((r) => ({ ...r, actual_end_at: e.target.value }))
              }
              required
              disabled={busy}
            />
          </div>

          <TextField
            label="Homework given"
            value={report.homework_assigned}
            onChange={(e) =>
              setReport((r) => ({ ...r, homework_assigned: e.target.value }))
            }
            placeholder="Optional"
            disabled={busy}
          />

          <div className="flex gap-3 pt-1">
            <Button
              type="button"
              variant="secondary"
              className="flex-1"
              onClick={() => setReportFor(null)}
              disabled={busy}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              className="flex-1"
              loading={busy}
              disabled={!report.topics_covered.trim()}
            >
              Submit report
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
