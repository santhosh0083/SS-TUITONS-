"use client";

import { useState } from "react";

import { Reveal } from "@/components/site/Reveal";
import { initialsOf, testimonials } from "@/data/testimonials";

const INITIAL_COUNT = 6;

export function Testimonials() {
  const [expanded, setExpanded] = useState(false);
  const shown = expanded ? testimonials : testimonials.slice(0, INITIAL_COUNT);
  const remaining = testimonials.length - INITIAL_COUNT;

  return (
    <section id="reviews" className="border-y border-ink-200 bg-white py-20">
      <div className="mx-auto max-w-6xl px-5">
        <Reveal>
          <h2 className="text-3xl font-semibold tracking-tight text-navy-900">
            What parents and students say
          </h2>
          <p className="mt-3 max-w-2xl text-[15px] text-ink-600">
            Unedited reviews from families across Hyderabad — home tuition,
            small batches and one-to-one coaching.
          </p>
        </Reveal>

        {/* Masonry via CSS columns: cards keep their natural height instead of
            being stretched to match the tallest in a row. */}
        <div className="mt-12 gap-6 sm:columns-2 lg:columns-3">
          {shown.map((t, i) => (
            <Reveal
              key={t.name}
              // Only stagger the first screenful; delaying card 18 by 1.4s
              // would just look broken.
              delay={i < INITIAL_COUNT ? i * 70 : 0}
              className="mb-6 break-inside-avoid"
            >
              <figure className="rounded-xl border border-ink-200 p-6 transition-all duration-200 ease-[var(--ease-out-soft)] hover:-translate-y-1 hover:shadow-[var(--shadow-lifted)]">
                <svg
                  className="h-6 w-6 text-gold-300"
                  viewBox="0 0 24 24"
                  fill="currentColor"
                  aria-hidden="true"
                >
                  <path d="M9.5 6C6.5 7.6 5 10 5 13v5h6v-6H8.4c.1-1.7.8-2.9 2.3-3.8L9.5 6Zm9 0c-3 1.6-4.5 4-4.5 7v5h6v-6h-2.6c.1-1.7.8-2.9 2.3-3.8L18.5 6Z" />
                </svg>

                <blockquote className="mt-3 text-[15px] leading-relaxed text-ink-700">
                  {t.quote}
                </blockquote>

                <figcaption className="mt-5 flex items-center gap-3 border-t border-ink-200 pt-4">
                  <span
                    aria-hidden="true"
                    className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-navy-900 text-xs font-semibold text-white"
                  >
                    {initialsOf(t.name)}
                  </span>
                  <span className="min-w-0">
                    <span className="block truncate text-sm font-medium text-navy-900">
                      {t.name}
                    </span>
                    <span className="block text-xs text-ink-500">{t.context}</span>
                  </span>
                </figcaption>
              </figure>
            </Reveal>
          ))}
        </div>

        {!expanded && remaining > 0 && (
          <div className="mt-4 text-center">
            <button
              type="button"
              onClick={() => setExpanded(true)}
              className="inline-flex h-11 items-center justify-center gap-2 rounded-lg border border-ink-300 px-5 text-sm font-medium text-navy-900 transition-all duration-150 hover:-translate-y-px hover:border-navy-300 hover:bg-ink-50"
            >
              Read {remaining} more reviews
              <svg
                className="h-4 w-4"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.8"
                strokeLinecap="round"
                strokeLinejoin="round"
                aria-hidden="true"
              >
                <path d="m6 9 6 6 6-6" />
              </svg>
            </button>
          </div>
        )}
      </div>
    </section>
  );
}
