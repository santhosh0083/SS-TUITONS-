"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

const NAV = [
  { href: "#courses", label: "Courses" },
  { href: "#how", label: "How it works" },
  { href: "#why", label: "Why us" },
  { href: "#contact", label: "Contact" },
];

export function Header() {
  const [scrolled, setScrolled] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 8);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <header
      className={[
        "sticky top-0 z-50 transition-all duration-200 ease-[var(--ease-out-soft)]",
        scrolled
          ? "border-b border-ink-200 bg-white/90 backdrop-blur-md"
          : "border-b border-transparent bg-transparent",
      ].join(" ")}
    >
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-5">
        <Link href="/" className="text-lg font-semibold tracking-tight text-navy-900">
          SS <span className="text-gold-600">TUITIONS</span>
        </Link>

        <nav className="hidden items-center gap-8 md:flex">
          {NAV.map((item) => (
            <a
              key={item.href}
              href={item.href}
              className="text-sm text-ink-600 transition-colors hover:text-navy-900"
            >
              {item.label}
            </a>
          ))}
          <Link
            href="/login"
            className="rounded-lg bg-navy-900 px-4 py-2 text-sm font-medium text-white transition-all duration-150 hover:-translate-y-px hover:bg-navy-800"
          >
            Sign in
          </Link>
        </nav>

        <button
          type="button"
          onClick={() => setMenuOpen((v) => !v)}
          className="md:hidden"
          aria-label={menuOpen ? "Close menu" : "Open menu"}
          aria-expanded={menuOpen}
        >
          <svg
            className="h-6 w-6 text-navy-900"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            viewBox="0 0 24 24"
            aria-hidden="true"
          >
            <path
              strokeLinecap="round"
              d={menuOpen ? "M6 6l12 12M18 6L6 18" : "M4 7h16M4 12h16M4 17h16"}
            />
          </svg>
        </button>
      </div>

      {menuOpen && (
        <div className="animate-[var(--animate-fade-in)] border-t border-ink-200 bg-white px-5 py-4 md:hidden">
          <nav className="flex flex-col gap-1">
            {NAV.map((item) => (
              <a
                key={item.href}
                href={item.href}
                onClick={() => setMenuOpen(false)}
                className="rounded-lg px-2 py-2.5 text-sm text-ink-700 hover:bg-ink-50"
              >
                {item.label}
              </a>
            ))}
            <Link
              href="/login"
              className="mt-2 rounded-lg bg-navy-900 px-4 py-2.5 text-center text-sm font-medium text-white"
            >
              Sign in
            </Link>
          </nav>
        </div>
      )}
    </header>
  );
}
