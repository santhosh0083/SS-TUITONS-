import type { ButtonHTMLAttributes, ReactNode } from "react";

type Variant = "primary" | "secondary" | "ghost" | "danger";
type Size = "sm" | "md" | "lg";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
  loading?: boolean;
  children: ReactNode;
}

const VARIANTS: Record<Variant, string> = {
  primary:
    "bg-navy-900 text-white hover:bg-navy-800 active:bg-navy-950 shadow-sm",
  secondary:
    "bg-white text-navy-900 border border-ink-300 hover:bg-ink-50 hover:border-ink-400",
  ghost: "bg-transparent text-navy-700 hover:bg-navy-50",
  danger: "bg-danger-500 text-white hover:bg-danger-700",
};

const SIZES: Record<Size, string> = {
  sm: "h-9 px-3 text-sm",
  md: "h-11 px-5 text-sm",
  lg: "h-12 px-6 text-base",
};

export function Button({
  variant = "primary",
  size = "md",
  loading = false,
  disabled,
  children,
  className = "",
  ...props
}: ButtonProps) {
  const isDisabled = disabled || loading;

  return (
    <button
      // `aria-busy` tells a screen reader the control is working. Without it,
      // a blind user gets silence after pressing Sign in.
      aria-busy={loading}
      disabled={isDisabled}
      className={[
        "inline-flex items-center justify-center gap-2 rounded-lg font-medium",
        "transition-all duration-150 ease-[var(--ease-out-soft)]",
        "disabled:cursor-not-allowed disabled:opacity-55",
        // Lift on hover, settle on press. Subtle enough to feel physical
        // rather than decorative.
        !isDisabled && "hover:-translate-y-px active:translate-y-0",
        VARIANTS[variant],
        SIZES[size],
        className,
      ]
        .filter(Boolean)
        .join(" ")}
      {...props}
    >
      {loading && (
        <svg
          className="h-4 w-4 animate-spin"
          viewBox="0 0 24 24"
          fill="none"
          aria-hidden="true"
        >
          <circle
            className="opacity-25"
            cx="12"
            cy="12"
            r="10"
            stroke="currentColor"
            strokeWidth="3"
          />
          <path
            className="opacity-90"
            fill="currentColor"
            d="M4 12a8 8 0 018-8v3a5 5 0 00-5 5H4z"
          />
        </svg>
      )}
      {children}
    </button>
  );
}
