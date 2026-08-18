"use client";

import { useEffect, useRef, type ReactNode } from "react";

interface ModalProps {
  open: boolean;
  title: string;
  description?: string;
  onClose: () => void;
  children: ReactNode;
}

export function Modal({ open, title, description, onClose, children }: ModalProps) {
  const panelRef = useRef<HTMLDivElement>(null);

  // onClose is usually an inline arrow function, so it is a new value on every
  // render of the parent. Holding it in a ref keeps it out of the effect
  // dependencies below.
  //
  // This mattered: with `onClose` in the deps, every keystroke in a form field
  // re-ran the effect, which called panelRef.focus() and pulled focus out of
  // the input. Typing was impossible after the first character.
  const onCloseRef = useRef(onClose);
  useEffect(() => {
    onCloseRef.current = onClose;
  }, [onClose]);

  // Escape closes, and the page behind must not scroll while a dialog is open —
  // otherwise on mobile the background slides around under your finger.
  // Depends on `open` alone, so it runs once per open/close, not per keystroke.
  useEffect(() => {
    if (!open) return;

    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onCloseRef.current();
    };
    document.addEventListener("keydown", onKey);

    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    // Move focus into the dialog so keyboard and screen-reader users are not
    // left behind on the page underneath. Focus the first field if there is
    // one, so the user can start typing immediately.
    const firstField = panelRef.current?.querySelector<HTMLElement>(
      "input:not([type=hidden]), textarea, select",
    );
    (firstField ?? panelRef.current)?.focus();

    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = previousOverflow;
    };
  }, [open]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto p-4 sm:p-6">
      <button
        type="button"
        aria-label="Close dialog"
        onClick={onClose}
        className="fixed inset-0 animate-[var(--animate-fade-in)] bg-navy-950/45 backdrop-blur-[2px]"
      />

      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-label={title}
        tabIndex={-1}
        className="relative my-8 w-full max-w-lg animate-[var(--animate-scale-in)] rounded-2xl bg-white shadow-[var(--shadow-lifted)] focus:outline-none"
      >
        <header className="flex items-start justify-between gap-4 border-b border-ink-200 px-6 py-5">
          <div>
            <h2 className="text-lg font-semibold text-navy-900">{title}</h2>
            {description && (
              <p className="mt-1 text-sm text-ink-500">{description}</p>
            )}
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close"
            className="-mr-1 rounded-lg p-1.5 text-ink-500 transition-colors hover:bg-ink-100 hover:text-ink-800"
          >
            <svg
              className="h-5 w-5"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.8"
              strokeLinecap="round"
              aria-hidden="true"
            >
              <path d="M6 6l12 12M18 6L6 18" />
            </svg>
          </button>
        </header>

        <div className="px-6 py-5">{children}</div>
      </div>
    </div>
  );
}
