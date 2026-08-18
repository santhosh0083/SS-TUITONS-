"use client";

import { ClassList } from "@/components/app/ClassList";
import { useAuth } from "@/lib/auth-context";

export default function StudentDashboard() {
  const { user } = useAuth();
  const firstName = user?.full_name.split(" ")[0] ?? "";

  return (
    <div className="mx-auto max-w-3xl">
      <header>
        <h1 className="text-2xl font-semibold tracking-tight text-navy-900">
          Hello{firstName && `, ${firstName}`}
        </h1>
        <p className="mt-1 text-sm text-ink-500">
          Your classes. Tap Join when it is time.
        </p>
      </header>

      <section className="mt-8">
        <h2 className="text-sm font-semibold uppercase tracking-wider text-ink-500">
          Today &amp; upcoming
        </h2>
        <div className="mt-4">
          <ClassList
            who="tutor"
            emptyTitle="No classes yet"
            emptyBody="Your classes will appear here once they are scheduled."
          />
        </div>
      </section>
    </div>
  );
}
