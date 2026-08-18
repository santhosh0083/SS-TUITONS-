"use client";

import { ClassList } from "@/components/app/ClassList";
import { useAuth } from "@/lib/auth-context";

export default function ParentDashboard() {
  const { user } = useAuth();
  const firstName = user?.full_name.split(" ")[0] ?? "";

  return (
    <div className="mx-auto max-w-3xl">
      <header>
        <h1 className="text-2xl font-semibold tracking-tight text-navy-900">
          Welcome{firstName && `, ${firstName}`}
        </h1>
        <p className="mt-1 text-sm text-ink-500">
          Your child&apos;s upcoming classes. Tap Join when the class is due.
        </p>
      </header>

      <section className="mt-8">
        <h2 className="text-sm font-semibold uppercase tracking-wider text-ink-500">
          Upcoming classes
        </h2>
        <div className="mt-4">
          <ClassList
            who="tutor"
            emptyTitle="No classes scheduled yet"
            emptyBody="Once SS Tuitions schedules a class, it appears here with a Join button."
          />
        </div>
      </section>

      <p className="mt-8 text-xs leading-relaxed text-ink-400">
        Messages to your tutor stay inside SS Tuitions — no phone numbers are
        exchanged. Administrators can review conversations for safety reasons,
        and every such access is recorded.
      </p>
    </div>
  );
}
