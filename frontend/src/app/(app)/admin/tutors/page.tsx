"use client";

import { useCallback, useEffect, useState } from "react";

import { CredentialsPanel } from "@/components/app/CredentialsPanel";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { TextField } from "@/components/ui/TextField";
import { ApiError, apiFetch } from "@/lib/api";

interface Tutor {
  id: string;
  full_name: string;
  email: string;
  phone: string | null;
  qualification: string | null;
  experience_years: number | null;
  is_contact_public: boolean;
  status: string;
  batches_assigned: number;
  students_reached: number;
}

interface Created {
  full_name: string;
  email: string;
  temporary_password: string;
}

export default function TutorsPage() {
  const [tutors, setTutors] = useState<Tutor[] | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  const [formOpen, setFormOpen] = useState(false);
  const [created, setCreated] = useState<Created | null>(null);

  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [qualification, setQualification] = useState("");
  const [experience, setExperience] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const load = useCallback(() => {
    apiFetch<Tutor[]>("/admin/tutors")
      .then(setTutors)
      .catch((e) =>
        setLoadError(e instanceof ApiError ? e.message : "Could not load tutors."),
      );
  }, []);

  useEffect(load, [load]);

  function resetForm() {
    setFullName("");
    setEmail("");
    setPhone("");
    setQualification("");
    setExperience("");
    setFormError(null);
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setFormError(null);
    setSubmitting(true);
    try {
      const result = await apiFetch<Created>("/admin/tutors", {
        method: "POST",
        body: {
          full_name: fullName,
          email,
          phone: phone || null,
          qualification: qualification || null,
          experience_years: experience ? Number(experience) : null,
          is_contact_public: false,
        },
      });
      setCreated(result);
      setFormOpen(false);
      resetForm();
      load();
    } catch (err) {
      setFormError(
        err instanceof ApiError ? err.message : "Could not create the tutor.",
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
            Tutors
          </h1>
          <p className="mt-1 text-sm text-ink-500">
            Tutors teach assigned batches, log what they taught, and mark
            attendance.
          </p>
        </div>
        <Button onClick={() => setFormOpen(true)}>Add tutor</Button>
      </header>

      {loadError && (
        <div
          role="alert"
          className="mt-6 rounded-xl border border-danger-500/25 bg-danger-50 px-4 py-3.5 text-sm text-danger-700"
        >
          {loadError}
        </div>
      )}

      {/* Loading */}
      {!tutors && !loadError && (
        <div className="mt-8 space-y-3">
          {[0, 1, 2].map((i) => (
            <div
              key={i}
              className="h-20 animate-pulse rounded-xl border border-ink-200 bg-white"
            />
          ))}
        </div>
      )}

      {/* Empty */}
      {tutors?.length === 0 && (
        <div className="mt-8 animate-[var(--animate-fade-up)] rounded-xl border border-dashed border-ink-300 bg-white px-6 py-14 text-center">
          <span className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-navy-50">
            <svg
              className="h-6 w-6 text-navy-600"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.5"
              aria-hidden="true"
            >
              <path d="M12 3 2 8l10 5 10-5-10-5Zm0 9.5L5 9v4.5c0 2 3.1 3.5 7 3.5s7-1.5 7-3.5V9" />
            </svg>
          </span>
          <h2 className="mt-4 font-semibold text-navy-900">No tutors yet</h2>
          <p className="mx-auto mt-1.5 max-w-sm text-sm text-ink-500">
            Add your first tutor to start creating batches and scheduling
            classes.
          </p>
          <Button className="mt-6" onClick={() => setFormOpen(true)}>
            Add your first tutor
          </Button>
        </div>
      )}

      {/* List */}
      {tutors && tutors.length > 0 && (
        <div className="mt-8 overflow-hidden rounded-xl border border-ink-200 bg-white shadow-[var(--shadow-card)]">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-ink-200 bg-ink-50">
              <tr className="text-xs uppercase tracking-wider text-ink-500">
                <th className="px-5 py-3 font-semibold">Tutor</th>
                <th className="hidden px-5 py-3 font-semibold sm:table-cell">
                  Qualification
                </th>
                <th className="px-5 py-3 text-right font-semibold">Batches</th>
                <th className="px-5 py-3 text-right font-semibold">Students</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-ink-200">
              {tutors.map((t) => (
                <tr key={t.id} className="transition-colors hover:bg-ink-50">
                  <td className="px-5 py-4">
                    <div className="font-medium text-ink-900">{t.full_name}</div>
                    <div className="text-xs text-ink-500">{t.email}</div>
                    {t.status !== "active" && (
                      <span className="mt-1 inline-block rounded bg-warning-50 px-1.5 py-0.5 text-[11px] font-medium text-warning-700">
                        {t.status}
                      </span>
                    )}
                  </td>
                  <td className="hidden px-5 py-4 text-ink-600 sm:table-cell">
                    {t.qualification ?? "—"}
                    {t.experience_years != null && (
                      <span className="block text-xs text-ink-500">
                        {t.experience_years} yr experience
                      </span>
                    )}
                  </td>
                  <td className="px-5 py-4 text-right tabular-nums text-ink-700">
                    {t.batches_assigned}
                  </td>
                  <td className="px-5 py-4 text-right tabular-nums text-ink-700">
                    {t.students_reached}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {tutors && tutors.length > 0 && (
        <p className="mt-4 text-xs text-ink-400">
          Tutor contact details are hidden from students and parents.
        </p>
      )}

      {/* ---------- Add tutor ---------- */}
      <Modal
        open={formOpen}
        title="Add tutor"
        description="A sign-in account is created and a temporary password shown once."
        onClose={() => setFormOpen(false)}
      >
        <form onSubmit={handleSubmit} className="space-y-4" noValidate>
          <TextField
            label="Full name"
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
            placeholder="Sai"
            required
            disabled={submitting}
          />
          <TextField
            label="Email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="tutor@example.com"
            hint="They sign in with this."
            required
            disabled={submitting}
          />
          <TextField
            label="Phone"
            value={phone}
            onChange={(e) => setPhone(e.target.value)}
            placeholder="Optional"
            disabled={submitting}
          />
          <TextField
            label="Qualification"
            value={qualification}
            onChange={(e) => setQualification(e.target.value)}
            placeholder="e.g. IIT Hyderabad, Computer Science"
            hint="Internal only — never shown to students or parents."
            disabled={submitting}
          />
          <TextField
            label="Years of experience"
            type="number"
            min={0}
            max={60}
            value={experience}
            onChange={(e) => setExperience(e.target.value)}
            placeholder="Optional"
            disabled={submitting}
          />

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
              onClick={() => setFormOpen(false)}
              disabled={submitting}
            >
              Cancel
            </Button>
            <Button type="submit" className="flex-1" loading={submitting}>
              Create tutor
            </Button>
          </div>
        </form>
      </Modal>

      {/* ---------- Credentials, shown once ---------- */}
      <Modal
        open={created !== null}
        title="Tutor created"
        description="Pass these details on now."
        onClose={() => setCreated(null)}
      >
        {created && (
          <CredentialsPanel
            credentials={[
              {
                label: created.full_name,
                email: created.email,
                password: created.temporary_password,
              },
            ]}
            onDone={() => setCreated(null)}
          />
        )}
      </Modal>
    </div>
  );
}
