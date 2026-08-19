"use client";

import { useCallback, useEffect, useState } from "react";

import { RemovePersonButton } from "@/components/app/RemovePersonButton";
import { table } from "@/components/ui/responsiveTable";
import { ApiError, apiFetch } from "@/lib/api";

interface Parent {
  id: string;
  user_id: string;
  full_name: string;
  email: string;
  phone: string | null;
  status: string;
  children: string[];
}

export default function ParentsPage() {
  const [parents, setParents] = useState<Parent[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showRemoved, setShowRemoved] = useState(false);

  const load = useCallback(() => {
    apiFetch<Parent[]>(
      `/admin/parents${showRemoved ? "?include_removed=true" : ""}`,
    )
      .then(setParents)
      .catch((e) =>
        setError(e instanceof ApiError ? e.message : "Could not load parents."),
      );
  }, [showRemoved]);

  useEffect(load, [load]);

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
        <div className={table.wrapper}>
          <table className={table.root}>
            <thead className={table.head}>
              <tr className="text-xs uppercase tracking-wider text-ink-500">
                <th className="px-5 py-3 font-semibold">Parent</th>
                <th className="px-5 py-3 font-semibold">Children</th>
                <th className="hidden px-5 py-3 font-semibold sm:table-cell">
                  Phone
                </th>
                <th className="px-5 py-3 text-right font-semibold">
                  <span className="sr-only">Actions</span>
                </th>
              </tr>
            </thead>
            <tbody className={table.body}>
              {parents.map((p) => (
                <tr key={p.id} className={table.row}>
                  <td className={table.cellPrimary}>
                    <div className="font-medium text-ink-900">{p.full_name}</div>
                    <div className="text-xs text-ink-500">{p.email}</div>
                  </td>
                  <td className={table.cell} data-label="Children">
                    <span>{p.children.length > 0 ? p.children.join(", ") : "—"}</span>
                  </td>
                  <td className={table.cell} data-label="Phone">
                    <span className="text-ink-600">{p.phone ?? "—"}</span>
                  </td>
                  <td className={table.cellAction}>
                    <RemovePersonButton
                      userId={p.user_id}
                      fullName={p.full_name}
                      removed={p.status === "suspended"}
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
          {showRemoved ? "Hide removed parents" : "Show removed parents"}
        </button>
      </div>
    </div>
  );
}
