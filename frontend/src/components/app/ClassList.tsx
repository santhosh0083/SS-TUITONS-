"use client";

import { useEffect, useState } from "react";

import { ClassCard, type ClassSession } from "@/components/app/ClassCard";
import { ApiError, apiFetch } from "@/lib/api";

/** Shared by the parent, tutor and student dashboards. The backend decides
 *  which classes each role may see; this only renders them. */
export function ClassList({
  who,
  emptyTitle,
  emptyBody,
}: {
  who: "tutor" | "student";
  emptyTitle: string;
  emptyBody: string;
}) {
  const [classes, setClasses] = useState<ClassSession[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    const load = () =>
      apiFetch<ClassSession[]>("/classes/mine")
        .then((d) => {
          if (!cancelled) setClasses(d);
        })
        .catch((e) => {
          if (!cancelled) {
            setError(
              e instanceof ApiError ? e.message : "Could not load your classes.",
            );
          }
        });

    load();
    // Refresh so the Join button appears when the class opens, without the
    // user needing to reload the page.
    const timer = setInterval(load, 60_000);
    return () => {
      cancelled = true;
      clearInterval(timer);
    };
  }, []);

  if (error) {
    return (
      <div
        role="alert"
        className="rounded-xl border border-danger-500/25 bg-danger-50 px-4 py-3.5 text-sm text-danger-700"
      >
        {error}
      </div>
    );
  }

  if (!classes) {
    return (
      <div className="space-y-4">
        {[0, 1].map((i) => (
          <div
            key={i}
            className="h-36 animate-pulse rounded-xl border border-ink-200 bg-white"
          />
        ))}
      </div>
    );
  }

  if (classes.length === 0) {
    return (
      <div className="animate-[var(--animate-fade-up)] rounded-xl border border-dashed border-ink-300 bg-white px-6 py-14 text-center">
        <span className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-navy-50">
          <svg
            className="h-6 w-6 text-navy-600"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.5"
            aria-hidden="true"
          >
            <path d="M8 2v4m8-4v4M3 9h18M5 5h14a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2Z" />
          </svg>
        </span>
        <h2 className="mt-4 font-semibold text-navy-900">{emptyTitle}</h2>
        <p className="mx-auto mt-1.5 max-w-sm text-sm text-ink-500">{emptyBody}</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {classes.map((c, i) => (
        <div
          key={c.id}
          className="animate-[var(--animate-fade-up)]"
          style={{ animationDelay: `${i * 60}ms` }}
        >
          <ClassCard session={c} who={who} />
        </div>
      ))}
    </div>
  );
}
