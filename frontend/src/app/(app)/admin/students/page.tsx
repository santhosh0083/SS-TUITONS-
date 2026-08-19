"use client";

import { useCallback, useEffect, useState } from "react";

import { CredentialsPanel } from "@/components/app/CredentialsPanel";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { SelectField } from "@/components/ui/SelectField";
import { TextField } from "@/components/ui/TextField";
import { RemovePersonButton } from "@/components/app/RemovePersonButton";
import { ApiError, apiFetch } from "@/lib/api";

interface Student {
  id: string;
  user_id: string;
  full_name: string;
  email: string;
  admission_no: string;
  grade: string;
  school_name: string | null;
  target_exam: string | null;
  status: string;
  batches: string[];
  parents: string[];
}

interface Person {
  full_name: string;
  email: string;
  temporary_password: string;
}

interface Created extends Person {
  admission_no: string;
  parent: Person | null;
}

interface Exam {
  id: string;
  name: string;
}

const GRADES = Array.from({ length: 12 }, (_, i) => ({
  value: String(i + 1),
  label: `Grade ${i + 1}`,
}));

export default function StudentsPage() {
  const [students, setStudents] = useState<Student[] | null>(null);
  const [showRemoved, setShowRemoved] = useState(false);
  const [exams, setExams] = useState<Exam[]>([]);
  const [loadError, setLoadError] = useState<string | null>(null);

  const [open, setOpen] = useState(false);
  const [created, setCreated] = useState<Created | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const [form, setForm] = useState({
    full_name: "",
    email: "",
    phone: "",
    grade: "11",
    school_name: "",
    target_exam_id: "",
    parent_full_name: "",
    parent_email: "",
    parent_phone: "",
  });

  const set = (k: keyof typeof form) => (v: string) =>
    setForm((f) => ({ ...f, [k]: v }));

  const load = useCallback(() => {
    apiFetch<Student[]>(
      `/admin/students${showRemoved ? "?include_removed=true" : ""}`,
    )
      .then(setStudents)
      .catch((e) =>
        setLoadError(e instanceof ApiError ? e.message : "Could not load students."),
      );
    apiFetch<Exam[]>("/admin/exams")
      .then(setExams)
      .catch(() => setExams([]));
  }, [showRemoved]);

  useEffect(load, [load]);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setFormError(null);
    setSubmitting(true);
    try {
      const result = await apiFetch<Created>("/admin/students", {
        method: "POST",
        body: {
          full_name: form.full_name,
          email: form.email,
          phone: form.phone || null,
          grade: form.grade,
          school_name: form.school_name || null,
          target_exam_id: form.target_exam_id || null,
          // Parent is created only when both name and email are given.
          parent_full_name: form.parent_full_name || null,
          parent_email: form.parent_email || null,
          parent_phone: form.parent_phone || null,
        },
      });
      setCreated(result);
      setOpen(false);
      setForm({
        full_name: "",
        email: "",
        phone: "",
        grade: "11",
        school_name: "",
        target_exam_id: "",
        parent_full_name: "",
        parent_email: "",
        parent_phone: "",
      });
      load();
    } catch (err) {
      setFormError(
        err instanceof ApiError ? err.message : "Could not create the student.",
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="mx-auto max-w-6xl">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-navy-900">
            Students
          </h1>
          <p className="mt-1 text-sm text-ink-500">
            Add a student and their parent together, so the parent can follow
            progress from day one.
          </p>
        </div>
        <Button onClick={() => setOpen(true)}>Add student</Button>
      </header>

      {loadError && (
        <div
          role="alert"
          className="mt-6 rounded-xl border border-danger-500/25 bg-danger-50 px-4 py-3.5 text-sm text-danger-700"
        >
          {loadError}
        </div>
      )}

      {!students && !loadError && (
        <div className="mt-8 space-y-3">
          {[0, 1, 2].map((i) => (
            <div
              key={i}
              className="h-20 animate-pulse rounded-xl border border-ink-200 bg-white"
            />
          ))}
        </div>
      )}

      {students?.length === 0 && (
        <div className="mt-8 animate-[var(--animate-fade-up)] rounded-xl border border-dashed border-ink-300 bg-white px-6 py-14 text-center">
          <h2 className="font-semibold text-navy-900">No students yet</h2>
          <p className="mx-auto mt-1.5 max-w-sm text-sm text-ink-500">
            Add your first student to start scheduling classes.
          </p>
          <Button className="mt-6" onClick={() => setOpen(true)}>
            Add your first student
          </Button>
        </div>
      )}

      {students && students.length > 0 && (
        <div className="mt-8 overflow-x-auto rounded-xl border border-ink-200 bg-white shadow-[var(--shadow-card)]">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-ink-200 bg-ink-50">
              <tr className="text-xs uppercase tracking-wider text-ink-500">
                <th className="px-5 py-3 font-semibold">Student</th>
                <th className="px-5 py-3 font-semibold">Grade</th>
                <th className="hidden px-5 py-3 font-semibold md:table-cell">
                  Parent
                </th>
                <th className="hidden px-5 py-3 font-semibold lg:table-cell">
                  Subjects
                </th>
                <th className="px-5 py-3 text-right font-semibold">
                  <span className="sr-only">Actions</span>
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-ink-200">
              {students.map((s) => (
                <tr key={s.id} className="transition-colors hover:bg-ink-50">
                  <td className="px-5 py-4">
                    <div className="font-medium text-ink-900">{s.full_name}</div>
                    <div className="text-xs text-ink-500">{s.admission_no}</div>
                  </td>
                  <td className="px-5 py-4 text-ink-700">
                    Grade {s.grade}
                    {s.target_exam && (
                      <span className="block text-xs text-ink-500">
                        {s.target_exam}
                      </span>
                    )}
                  </td>
                  <td className="hidden px-5 py-4 text-ink-600 md:table-cell">
                    {s.parents.length > 0 ? (
                      s.parents.join(", ")
                    ) : (
                      <span className="text-warning-700">No parent linked</span>
                    )}
                  </td>
                  <td className="hidden px-5 py-4 text-ink-600 lg:table-cell">
                    {s.batches.length > 0 ? s.batches.join(", ") : "—"}
                  </td>
                  <td className="px-5 py-4 text-right">
                    <RemovePersonButton
                      userId={s.user_id}
                      fullName={s.full_name}
                      removed={s.status === "suspended"}
                      onDone={load}
                    />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div className="mt-4 flex justify-end">
        <button
          type="button"
          onClick={() => setShowRemoved((v) => !v)}
          className="text-xs font-medium text-ink-500 underline-offset-4 hover:text-navy-700 hover:underline"
        >
          {showRemoved ? "Hide removed students" : "Show removed students"}
        </button>
      </div>

      {/* ---------- Add student ---------- */}
      <Modal
        open={open}
        title="Add student"
        description="Sign-in accounts are created for the student and parent."
        onClose={() => setOpen(false)}
      >
        <form onSubmit={submit} className="space-y-4" noValidate>
          <TextField
            label="Student's full name"
            value={form.full_name}
            onChange={(e) => set("full_name")(e.target.value)}
            placeholder="Rahul"
            required
            disabled={submitting}
          />
          <TextField
            label="Student's email"
            type="email"
            value={form.email}
            onChange={(e) => set("email")(e.target.value)}
            placeholder="student@example.com"
            hint="They sign in with this."
            required
            disabled={submitting}
          />
          <div className="grid gap-4 sm:grid-cols-2">
            <SelectField
              label="Grade"
              value={form.grade}
              onChange={(e) => set("grade")(e.target.value)}
              options={GRADES}
              disabled={submitting}
            />
            <SelectField
              label="Target exam"
              value={form.target_exam_id}
              onChange={(e) => set("target_exam_id")(e.target.value)}
              options={exams.map((x) => ({ value: x.id, label: x.name }))}
              placeholder="Not decided"
              disabled={submitting}
            />
          </div>
          <TextField
            label="School"
            value={form.school_name}
            onChange={(e) => set("school_name")(e.target.value)}
            placeholder="Optional"
            disabled={submitting}
          />

          <div className="rounded-lg border border-ink-200 bg-ink-50 p-4">
            <p className="text-sm font-medium text-ink-800">Parent</p>
            <p className="mt-0.5 text-xs text-ink-500">
              Optional, but without a parent account there is nobody to message
              or show progress to.
            </p>
            <div className="mt-3 space-y-3">
              <TextField
                label="Parent's full name"
                value={form.parent_full_name}
                onChange={(e) => set("parent_full_name")(e.target.value)}
                placeholder="Optional"
                disabled={submitting}
              />
              <TextField
                label="Parent's email"
                type="email"
                value={form.parent_email}
                onChange={(e) => set("parent_email")(e.target.value)}
                placeholder="Optional"
                disabled={submitting}
              />
              <TextField
                label="Parent's phone"
                value={form.parent_phone}
                onChange={(e) => set("parent_phone")(e.target.value)}
                placeholder="Optional"
                hint="Kept private. Never shown to tutors."
                disabled={submitting}
              />
            </div>
          </div>

          {formError && (
            <div
              role="alert"
              className="rounded-lg border border-danger-500/25 bg-danger-50 px-3.5 py-3 text-sm text-danger-700"
            >
              {formError}
            </div>
          )}

          <div className="flex gap-3 pt-1">
            <Button
              type="button"
              variant="secondary"
              className="flex-1"
              onClick={() => setOpen(false)}
              disabled={submitting}
            >
              Cancel
            </Button>
            <Button type="submit" className="flex-1" loading={submitting}>
              Create student
            </Button>
          </div>
        </form>
      </Modal>

      {/* ---------- Credentials ---------- */}
      <Modal
        open={created !== null}
        title="Student created"
        description="Pass these details on now."
        onClose={() => setCreated(null)}
      >
        {created && (
          <CredentialsPanel
            credentials={[
              {
                label: `${created.full_name} · Student · ${created.admission_no}`,
                email: created.email,
                password: created.temporary_password,
              },
              ...(created.parent
                ? [
                    {
                      label: `${created.parent.full_name} · Parent`,
                      email: created.parent.email,
                      password: created.parent.temporary_password,
                    },
                  ]
                : []),
            ]}
            onDone={() => setCreated(null)}
          />
        )}
      </Modal>
    </div>
  );
}
