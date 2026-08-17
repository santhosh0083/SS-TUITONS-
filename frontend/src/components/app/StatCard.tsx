import Link from "next/link";
import type { ReactNode } from "react";

interface StatCardProps {
  label: string;
  value: number;
  icon: ReactNode;
  href?: string;
  /** Draws attention when the number is something the owner must act on. */
  attention?: boolean;
  hint?: string;
}

export function StatCard({
  label,
  value,
  icon,
  href,
  attention = false,
  hint,
}: StatCardProps) {
  // Only highlight when there is genuinely something waiting. A permanently
  // amber card is decoration; people stop seeing it.
  const needsAction = attention && value > 0;

  const body = (
    <div
      className={[
        "h-full rounded-xl border bg-white p-5 transition-all duration-200 ease-[var(--ease-out-soft)]",
        needsAction
          ? "border-warning-500/40 bg-warning-50"
          : "border-ink-200 shadow-[var(--shadow-card)]",
        href ? "hover:-translate-y-0.5 hover:shadow-[var(--shadow-lifted)]" : "",
      ].join(" ")}
    >
      <div className="flex items-start justify-between">
        <span
          className={[
            "inline-flex h-9 w-9 items-center justify-center rounded-lg",
            needsAction ? "bg-warning-500/15 text-warning-700" : "bg-navy-50 text-navy-700",
          ].join(" ")}
        >
          <svg
            className="h-[18px] w-[18px]"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.6"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
          >
            {icon}
          </svg>
        </span>

        {needsAction && (
          <span className="rounded-full bg-warning-500/15 px-2 py-0.5 text-[11px] font-medium text-warning-700">
            Needs action
          </span>
        )}
      </div>

      <p className="mt-4 text-3xl font-semibold tracking-tight text-navy-900 tabular-nums">
        {value}
      </p>
      <p className="mt-0.5 text-sm text-ink-600">{label}</p>
      {hint && <p className="mt-2 text-xs leading-relaxed text-ink-500">{hint}</p>}
    </div>
  );

  return href ? (
    <Link href={href} className="block h-full">
      {body}
    </Link>
  ) : (
    body
  );
}
