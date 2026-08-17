"use client";

import { useId, type InputHTMLAttributes } from "react";

interface TextFieldProps extends InputHTMLAttributes<HTMLInputElement> {
  label: string;
  error?: string;
  hint?: string;
}

export function TextField({
  label,
  error,
  hint,
  className = "",
  ...props
}: TextFieldProps) {
  const id = useId();
  const errorId = `${id}-error`;
  const hintId = `${id}-hint`;

  return (
    <div className="w-full">
      <label
        htmlFor={id}
        className="mb-1.5 block text-sm font-medium text-ink-700"
      >
        {label}
      </label>

      <input
        id={id}
        // Ties the message to the field so a screen reader announces it on
        // focus, instead of the user hearing only "edit text, blank".
        aria-invalid={error ? true : undefined}
        aria-describedby={
          [error ? errorId : null, hint ? hintId : null]
            .filter(Boolean)
            .join(" ") || undefined
        }
        className={[
          "w-full rounded-lg border bg-white px-3.5 py-2.5 text-[15px] text-ink-900",
          "placeholder:text-ink-400",
          "transition-colors duration-150",
          "focus:outline-none focus:ring-2 focus:ring-offset-1",
          error
            ? "border-danger-500 focus:border-danger-500 focus:ring-danger-500/30"
            : "border-ink-300 hover:border-ink-400 focus:border-navy-500 focus:ring-navy-500/25",
          className,
        ].join(" ")}
        {...props}
      />

      {hint && !error && (
        <p id={hintId} className="mt-1.5 text-xs text-ink-500">
          {hint}
        </p>
      )}

      {error && (
        <p
          id={errorId}
          className="mt-1.5 flex items-start gap-1.5 text-xs text-danger-700"
        >
          {/* An icon as well as colour, so the error is not conveyed by hue alone. */}
          <svg
            className="mt-px h-3.5 w-3.5 shrink-0"
            viewBox="0 0 20 20"
            fill="currentColor"
            aria-hidden="true"
          >
            <path
              fillRule="evenodd"
              d="M10 18a8 8 0 100-16 8 8 0 000 16zM9 9a1 1 0 012 0v4a1 1 0 11-2 0V9zm1-4a1 1 0 100 2 1 1 0 000-2z"
              clipRule="evenodd"
            />
          </svg>
          {error}
        </p>
      )}
    </div>
  );
}
