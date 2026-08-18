"use client";

import { useCallback, useEffect, useState } from "react";

import { ClassCard, type ClassSession } from "@/components/app/ClassCard";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { SelectField } from "@/components/ui/SelectField";
import { TextField } from "@/components/ui/TextField";
import { ApiError, apiFetch } from "@/lib/api";

interface Student {
  id: string;
  full_name: string;
  admission_no: string;
  grade: string;
  batches: string[];
}
interface Tutor {
  id: string;
  full_name: string;
}
interface Subject {
  id: string;
  name: string;
}
interface Assignment {
  batch_id: string;
  batch_code: string;
  conversation_id: string | null;
  conversation_note: string;
}

export default function ClassesPage() {
  const [classes, setClasses] = useState<ClassSession[] | null>(null);
  const [students, setStudents] = useState<Student[]>([]);
  const [tutors, setTutors] = useState<Tutor[]>([]);
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [loadError, setLoadError] = useState<string | null>(null);

  const [assignOpen, setAssignOpen] = useState(false);
  const [assignForm, setAssignForm] = useState({
    student_id: "",
    tutor_id: "",
    subject_id: "",
  });
  const [assignResult, setAssignResult] = useState<Assignment | null>(null);

  const [scheduleOpen, setScheduleOpen] = useState(false);
  const [scheduleForm, setScheduleForm] = useState({
    scheduled_date: new Date().toISOString().slice(0, 10),
    scheduled_start: "19:00",
    scheduled_end: "20:00",
    meeting_url: "",
  });

  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    apiFetch<ClassSession[]>("/classes/mine")
      .then(setClasses)
      .catch((e) =>
        setLoadError(e instanceof ApiError ? e.message : "Could not load classes."),
      );
    apiFetch<Student[]>("/admin/students").then(setStudents).catch(() => {});
    apiFetch<Tutor[]>("/admin/tutors").then(setTutors).catch(() => {});
    apiFetch<Subject[]>("/admin/subjects").then(setSubjects).catch(() => {});
  }, []);

  useEffect(load, [load]);

  async function submitAssign(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      const result = await apiFetch<Assignment>("/assignments", {
        method: "POST",
        body: assignForm,
      });
      setAssignResult(result);
      setAssignOpen(false);
      setScheduleOpen(true); // straight into scheduling the first class
      load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not assign the tutor.");
    } finally {
      setBusy(false);
    }
  }

  async function submitSchedule(e: React.FormEvent) {
    e.preventDefault();
    if (!assignResult) return;
    setError(null);
    setBusy(true);
    try {
      await apiFetch("/classes", {
        method: "POST",
        body: {
          batch_id: assignResult.batch_id,
          tutor_id: assignForm.tutor_id,
          subject_id: assignForm.subject_id,
          scheduled_date: scheduleForm.scheduled_date,
          scheduled_start: scheduleForm.scheduled_start,
          scheduled_end: scheduleForm.scheduled_end,
          meeting_url: scheduleForm.meeting_url.trim() || null,
        },
      });
      setScheduleOpen(false);
      setAssignResult(null);
      setAssignForm({ student_id: "", tutor_id: "", subject_id: "" });
      load();
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "Could not schedule the class.",
      );
    } finally {
      setBusy(false);
    }
  }

  const canAssign = students.length > 0 && tutors.length > 0;

  return (
    <div className="mx-auto max-w-4xl">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-navy-900">
            Classes
          </h1>
          <p className="mt-1 text-sm text-ink-500">
            Assign a tutor, then schedule the class. Both sides see it
            immediately.
          </p>
        </div>
        <Button onClick={() => setAssignOpen(true)} disabled={!canAssign}>
          Assign tutor
        </Button>
      </header>

      {!canAssign && (
        <p className="mt-4 rounded-lg border border-warning-500/30 bg-warning-50 px-4 py-3 text-sm text-warning-700">
          Add at least one student and one tutor before assigning.
        </p>
      )}

      {(error || loadError) && (
        <div
          role="alert"
          className="mt-6 rounded-xl border border-danger-500/25 bg-danger-50 px-4 py-3.5 text-sm text-danger-700"
        >
          {error ?? loadError}
        </div>
      )}

      <section className="mt-8">
        <h2 className="text-sm font-semibold uppercase tracking-wider text-ink-500">
          Upcoming classes
        </h2>
        <div className="mt-4 space-y-4">
          {!classes && (
            <div className="h-36 animate-pulse rounded-xl border border-ink-200 bg-white" />
          )}
          {classes?.length === 0 && (
            <div className="rounded-xl border border-dashed border-ink-300 bg-white px-6 py-12 text-center">
              <h3 className="font-semibold text-navy-900">
                No classes scheduled
              </h3>
              <p className="mx-auto mt-1.5 max-w-sm text-sm text-ink-500">
                Assign a tutor to a student, then schedule the first class.
              </p>
            </div>
          )}
          {classes?.map((c) => (
            <ClassCard key={c.id} session={c} who="student" />
          ))}
        </div>
      </section>

      {/* ---------- Step 1: assign ---------- */}
      <Modal
        open={assignOpen}
        title="Assign tutor"
        description="Creates the batch and a private parent–tutor conversation."
        onClose={() => setAssignOpen(false)}
      >
        <form onSubmit={submitAssign} className="space-y-4" noValidate>
          <SelectField
            label="Student"
            value={assignForm.student_id}
            onChange={(e) =>
              setAssignForm((f) => ({ ...f, student_id: e.target.value }))
            }
            options={students.map((s) => ({
              value: s.id,
              label: `${s.full_name} · Grade ${s.grade}`,
            }))}
            placeholder="Choose a student"
            required
            disabled={busy}
          />
          <SelectField
            label="Tutor"
            value={assignForm.tutor_id}
            onChange={(e) =>
              setAssignForm((f) => ({ ...f, tutor_id: e.target.value }))
            }
            options={tutors.map((t) => ({ value: t.id, label: t.full_name }))}
            placeholder="Choose a tutor"
            required
            disabled={busy}
          />
          <SelectField
            label="Subject"
            value={assignForm.subject_id}
            onChange={(e) =>
              setAssignForm((f) => ({ ...f, subject_id: e.target.value }))
            }
            options={subjects.map((s) => ({ value: s.id, label: s.name }))}
            placeholder="Choose a subject"
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

          <div className="flex gap-3 pt-1">
            <Button
              type="button"
              variant="secondary"
              className="flex-1"
              onClick={() => setAssignOpen(false)}
              disabled={busy}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              className="flex-1"
              loading={busy}
              disabled={
                !assignForm.student_id ||
                !assignForm.tutor_id ||
                !assignForm.subject_id
              }
            >
              Assign
            </Button>
          </div>
        </form>
      </Modal>

      {/* ---------- Step 2: schedule ---------- */}
      <Modal
        open={scheduleOpen}
        title="Schedule the first class"
        description={assignResult?.conversation_note}
        onClose={() => setScheduleOpen(false)}
      >
        <form onSubmit={submitSchedule} className="space-y-4" noValidate>
          <TextField
            label="Date"
            type="date"
            value={scheduleForm.scheduled_date}
            onChange={(e) =>
              setScheduleForm((f) => ({ ...f, scheduled_date: e.target.value }))
            }
            required
            disabled={busy}
          />
          <div className="grid grid-cols-2 gap-4">
            <TextField
              label="Starts"
              type="time"
              value={scheduleForm.scheduled_start}
              onChange={(e) =>
                setScheduleForm((f) => ({ ...f, scheduled_start: e.target.value }))
              }
              required
              disabled={busy}
            />
            <TextField
              label="Ends"
              type="time"
              value={scheduleForm.scheduled_end}
              onChange={(e) =>
                setScheduleForm((f) => ({ ...f, scheduled_end: e.target.value }))
              }
              required
              disabled={busy}
            />
          </div>

          <TextField
            label="Google Meet link"
            value={scheduleForm.meeting_url}
            onChange={(e) =>
              setScheduleForm((f) => ({ ...f, meeting_url: e.target.value }))
            }
            placeholder="https://meet.google.com/abc-defg-hij"
            hint="Open meet.google.com, start a new meeting, paste the link. Leave empty to add it later."
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

          <div className="flex gap-3 pt-1">
            <Button
              type="button"
              variant="secondary"
              className="flex-1"
              onClick={() => setScheduleOpen(false)}
              disabled={busy}
            >
              Later
            </Button>
            <Button type="submit" className="flex-1" loading={busy}>
              Schedule class
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
