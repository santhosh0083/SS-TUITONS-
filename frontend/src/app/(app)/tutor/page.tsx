"use client";

import { ClassList } from "@/components/app/ClassList";
import { useAuth } from "@/lib/auth-context";

export default function TutorDashboard() {
  const { user } = useAuth();
  const firstName = user?.full_name.split(" ")[0] ?? "";

  return (
    <div className="mx-auto max-w-3xl">
      <header>
        <h1 className="text-2xl font-semibold tracking-tight text-navy-900">
          Welcome{firstName && `, ${firstName}`}
        </h1>
        <p className="mt-1 text-sm text-ink-500">
          Your scheduled classes. Tap Join to start teaching.
        </p>
      </header>

      <section className="mt-8">
        <h2 className="text-sm font-semibold uppercase tracking-wider text-ink-500">
          Your classes
        </h2>
        <div className="mt-4">
          <ClassList
            who="student"
            emptyTitle="No classes assigned yet"
            emptyBody="When SS Tuitions assigns you a student and schedules a class, it appears here."
          />
        </div>
      </section>
    </div>
  );
}
