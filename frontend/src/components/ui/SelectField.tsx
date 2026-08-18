"use client";

import { useId, type SelectHTMLAttributes } from "react";

export interface Option {
  value: string;
  label: string;
}

interface SelectFieldProps extends SelectHTMLAttributes<HTMLSelectElement> {
  label: string;
  options: Option[];
  error?: string;
  hint?: string;
  placeholder?: string;
}

export function SelectField({
  label,
  options,
  error,
  hint,
  placeholder,
  className = "",
  ...props
}: SelectFieldProps) {
  const id = useId();
  const errorId = `${id}-error`;
  const hintId = `${id}-hint`;

  return (
    <div className="w-full">
      <label htmlFor={id} className="mb-1.5 block text-sm font-medium text-ink-700">
        {label}
      </label>

      <select
        id={id}
        aria-invalid={error ? true : undefined}
        aria-describedby={
          [error ? errorId : null, hint ? hintId : null].filter(Boolean).join(" ") ||
          undefined
        }
        className={[
          "w-full appearance-none rounded-lg border bg-white px-3.5 py-2.5 text-[15px] text-ink-900",
          "bg-[url('data:image/svg+xml;utf8,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 24 24%22 fill=%22none%22 stroke=%22%236f7785%22 stroke-width=%221.8%22><path d=%22m6 9 6 6 6-6%22/></svg>')] bg-[length:18px] bg-[right_0.75rem_center] bg-no-repeat pr-10",
          "transition-colors duration-150 focus:outline-none focus:ring-2 focus:ring-offset-1",
          error
            ? "border-danger-500 focus:border-danger-500 focus:ring-danger-500/30"
            : "border-ink-300 hover:border-ink-400 focus:border-navy-500 focus:ring-navy-500/25",
          className,
        ].join(" ")}
        {...props}
      >
        {placeholder && <option value="">{placeholder}</option>}
        {options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>

      {hint && !error && (
        <p id={hintId} className="mt-1.5 text-xs text-ink-500">
          {hint}
        </p>
      )}
      {error && (
        <p id={errorId} className="mt-1.5 text-xs text-danger-700">
          {error}
        </p>
      )}
    </div>
  );
}
