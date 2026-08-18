"use client";

import { useEffect, useState } from "react";

import { ApiError, apiFetch } from "@/lib/api";

interface Parent {
  id: string;
  full_name: string;
  email: string;
  phone: string | null;
  status: string;
  children: string[];
}

export default function ParentsPage() {
  const [parents, setParents] = useState<Parent[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiFetch<Parent[]>("/admin/parents")
      .then(setParents)
      .catch((e) =>
        setError(e instanceof ApiError ? e.message : "Could not load parents."),
      );
  }, []);

  return (
    <div className="mx-auto max-w-6xl">
      <header>
        <h1 className="text-2xl font-semibold tracking-tight text-navy-900">
          Parents
        </h1>
        <p className="mt-1 text-sm text-ink-500">
          Parents are created alongside a student. Their contact details are
          never shown to tutors.
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

      {!parents && !error && (
        <div className="mt-8 space-y-3">
          {[0, 1].map((i) => (
            <div
              key={i}
              className="h-20 animate-pulse rounded-xl border border-ink-200 bg-white"
            />
          ))}
        </div>
      )}

      {parents?.length === 0 && (
        <div className="mt-8 animate-[var(--animate-fade-up)] rounded-xl border border-dashed border-ink-300 bg-white px-6 py-14 text-center">
          <h2 className="font-semibold text-navy-900">No parents yet</h2>
          <p className="mx-auto mt-1.5 max-w-sm text-sm text-ink-500">
            Add a student and fill in the parent section to create one.
          </p>
        </div>
      )}

      {parents && parents.length > 0 && (
        <div className="mt-8 overflow-x-auto rounded-xl border border-ink-200 bg-white shadow-[var(--shadow-card)]">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-ink-200 bg-ink-50">
              <tr className="text-xs uppercase tracking-wider text-ink-500">
                <th className="px-5 py-3 font-semibold">Parent</th>
                <th className="px-5 py-3 font-semibold">Children</th>
                <th className="hidden px-5 py-3 font-semibold sm:table-cell">
                  Phone
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-ink-200">
              {parents.map((p) => (
                <tr key={p.id} className="transition-colors hover:bg-ink-50">
                  <td className="px-5 py-4">
                    <div className="font-medium text-ink-900">{p.full_name}</div>
                    <div className="text-xs text-ink-500">{p.email}</div>
                  </td>
                  <td className="px-5 py-4 text-ink-700">
                    {p.children.length > 0 ? p.children.join(", ") : "—"}
                  </td>
                  <td className="hidden px-5 py-4 text-ink-600 sm:table-cell">
                    {p.phone ?? "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
