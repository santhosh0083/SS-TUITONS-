import Link from "next/link";

import { Header } from "@/components/site/Header";
import { Reveal } from "@/components/site/Reveal";
import { site, whatsappLink } from "@/lib/site";

/*
  Public homepage.

  Every claim here is one SS Tuitions can stand behind. Deliberately absent:
  student counts, exam ranks, success percentages, testimonials, and tutor
  names. Those are either not true yet or are private, and inventing them
  becomes a liability the moment a parent asks.

  Contact details come from lib/site.ts. Fees are not shown at all until the
  owner supplies them (docs/INTAKE.md Group E) — a wrong number on a public
  page is worse than no number.
*/

const HIGHLIGHTS = [
  {
    title: "IIT tutors",
    body: "Learn from tutors who cleared the exams they teach, alongside experienced professional teachers.",
    icon: <path d="M12 3 2 8l10 5 10-5-10-5Zm0 9.5L5 9v4.5c0 2 3.1 3.5 7 3.5s7-1.5 7-3.5V9l-7 3.5Z" />,
  },
  {
    title: "Every subject, Grade 1 to 12",
    body: "Maths, Physics, Chemistry, Biology, English, Social, Computer Science and more — one subject or all of them.",
    icon: <path d="M4 4h7v16H4V4Zm9 0h7v16h-7V4ZM6 7h3M6 10h3m6-3h3m-3 3h3" />,
  },
  {
    title: "Flexible timings",
    body: "Classes scheduled around school, not against it. Early mornings, evenings and weekends.",
    icon: <path d="M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18Zm0-14v5l3.5 2" />,
  },
  {
    title: "Affordable fees",
    body: "Small-batch pricing that works for families, with one-to-one available when your child needs it.",
    icon: <path d="M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18Zm3-12H10.5a2 2 0 0 0 0 4h3a2 2 0 0 1 0 4H9m3-10V6m0 12v-1" />,
  },
];

const STAGES = [
  {
    grades: "Grades 1 – 5",
    heading: "Foundation",
    points: ["Reading, writing and number sense", "Daily homework support", "Confidence before speed"],
  },
  {
    grades: "Grades 6 – 10",
    heading: "School & Board",
    points: ["All subjects covered", "Chapter-wise tests", "Board exam preparation"],
  },
  {
    grades: "Grades 11 – 12",
    heading: "Competitive",
    points: ["JEE Main & Advanced", "NEET, EAMCET / TG EAPCET", "IPE and SAT"],
  },
];

const STEPS = [
  { n: "1", t: "Tell us what you need", d: "Your child's grade, the subjects, and timings that suit your family." },
  { n: "2", t: "Meet the tutor", d: "A free trial class, so you can judge the teaching before committing." },
  { n: "3", t: "Start learning", d: "Regular classes, with attendance and progress you can check any time." },
];

function Icon({ children }: { children: React.ReactNode }) {
  return (
    <svg
      className="h-5 w-5"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      {children}
    </svg>
  );
}

export default function HomePage() {
  return (
    <>
      <Header />

      <main>
        {/* ---------------- Hero ---------------- */}
        <section className="relative overflow-hidden bg-navy-900">
          {/* Low-contrast grid: texture, not decoration. */}
          <div
            aria-hidden="true"
            className="pointer-events-none absolute inset-0 opacity-[0.06]"
            style={{
              backgroundImage:
                "linear-gradient(to right, white 1px, transparent 1px), linear-gradient(to bottom, white 1px, transparent 1px)",
              backgroundSize: "56px 56px",
            }}
          />

          <div className="relative mx-auto max-w-6xl px-5 py-20 sm:py-28">
            <div className="max-w-2xl">
              <span className="inline-flex animate-[var(--animate-fade-in)] items-center gap-2 rounded-full border border-gold-400/30 bg-gold-400/10 px-3 py-1 text-xs font-medium text-gold-300">
                Home &amp; online tuition · Grade 1 to 12
              </span>

              <h1 className="mt-6 animate-[var(--animate-fade-up)] text-4xl font-semibold leading-[1.12] tracking-tight text-white sm:text-5xl">
                Tuition that fits your child,
                <br />
                <span className="text-gold-400">and your schedule.</span>
              </h1>

              <p
                className="mt-6 max-w-xl animate-[var(--animate-fade-up)] text-[17px] leading-relaxed text-navy-200"
                style={{ animationDelay: "100ms" }}
              >
                One-to-one and small-batch classes across every subject, taught
                by IIT tutors and experienced professional teachers. Online
                anywhere, or at home.
              </p>

              <div
                className="mt-9 flex animate-[var(--animate-fade-up)] flex-col gap-3 sm:flex-row"
                style={{ animationDelay: "180ms" }}
              >
                <a
                  href="#contact"
                  className="inline-flex h-12 items-center justify-center rounded-lg bg-gold-500 px-6 text-sm font-semibold text-navy-950 transition-all duration-150 hover:-translate-y-px hover:bg-gold-400"
                >
                  Book a free trial class
                </a>
                <Link
                  href="/login"
                  className="inline-flex h-12 items-center justify-center rounded-lg border border-white/20 px-6 text-sm font-medium text-white transition-all duration-150 hover:-translate-y-px hover:bg-white/10"
                >
                  Student &amp; parent sign in
                </Link>
              </div>

              <div
                className="mt-10 flex animate-[var(--animate-fade-up)] flex-wrap gap-x-7 gap-y-2 text-sm text-navy-300"
                style={{ animationDelay: "260ms" }}
              >
                {["All subjects", "Flexible timings", "Affordable fees", "Online or at home"].map((t) => (
                  <span key={t} className="flex items-center gap-2">
                    <span className="h-1 w-1 rounded-full bg-gold-400" />
                    {t}
                  </span>
                ))}
              </div>
            </div>
          </div>
        </section>

        {/* ---------------- Highlights ---------------- */}
        <section id="why" className="mx-auto max-w-6xl px-5 py-20">
          <Reveal>
            <h2 className="text-3xl font-semibold tracking-tight text-navy-900">
              Why families choose SS Tuitions
            </h2>
          </Reveal>

          <div className="mt-12 grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
            {HIGHLIGHTS.map((item, i) => (
              <Reveal key={item.title} delay={i * 80}>
                <div className="group h-full rounded-xl border border-ink-200 bg-white p-6 shadow-[var(--shadow-card)] transition-all duration-200 ease-[var(--ease-out-soft)] hover:-translate-y-1 hover:shadow-[var(--shadow-lifted)]">
                  <span className="inline-flex h-10 w-10 items-center justify-center rounded-lg bg-navy-50 text-navy-700 transition-colors group-hover:bg-navy-900 group-hover:text-gold-400">
                    <Icon>{item.icon}</Icon>
                  </span>
                  <h3 className="mt-4 font-semibold text-navy-900">{item.title}</h3>
                  <p className="mt-2 text-sm leading-relaxed text-ink-600">{item.body}</p>
                </div>
              </Reveal>
            ))}
          </div>
        </section>

        {/* ---------------- Stages ---------------- */}
        <section id="courses" className="border-y border-ink-200 bg-white py-20">
          <div className="mx-auto max-w-6xl px-5">
            <Reveal>
              <h2 className="text-3xl font-semibold tracking-tight text-navy-900">
                From first steps to entrance exams
              </h2>
              <p className="mt-3 max-w-2xl text-[15px] text-ink-600">
                The same tutors follow your child through school, so nothing has
                to be explained twice.
              </p>
            </Reveal>

            <div className="mt-12 grid gap-6 lg:grid-cols-3">
              {STAGES.map((stage, i) => (
                <Reveal key={stage.grades} delay={i * 100}>
                  <div className="h-full rounded-xl border border-ink-200 p-7 transition-all duration-200 ease-[var(--ease-out-soft)] hover:-translate-y-1 hover:border-navy-300 hover:shadow-[var(--shadow-lifted)]">
                    <span className="text-xs font-semibold uppercase tracking-wider text-gold-600">
                      {stage.grades}
                    </span>
                    <h3 className="mt-2 text-xl font-semibold text-navy-900">{stage.heading}</h3>
                    <ul className="mt-5 space-y-2.5">
                      {stage.points.map((p) => (
                        <li key={p} className="flex gap-2.5 text-sm text-ink-600">
                          <svg
                            className="mt-1 h-3.5 w-3.5 shrink-0 text-gold-500"
                            viewBox="0 0 20 20"
                            fill="currentColor"
                            aria-hidden="true"
                          >
                            <path
                              fillRule="evenodd"
                              d="M16.7 5.3a1 1 0 010 1.4l-7.5 7.5a1 1 0 01-1.4 0L3.3 9.7a1 1 0 111.4-1.4l3.8 3.8 6.8-6.8a1 1 0 011.4 0z"
                              clipRule="evenodd"
                            />
                          </svg>
                          {p}
                        </li>
                      ))}
                    </ul>
                  </div>
                </Reveal>
              ))}
            </div>
          </div>
        </section>

        {/* ---------------- How it works ---------------- */}
        <section id="how" className="mx-auto max-w-6xl px-5 py-20">
          <Reveal>
            <h2 className="text-3xl font-semibold tracking-tight text-navy-900">How it works</h2>
          </Reveal>

          <div className="mt-12 grid gap-8 sm:grid-cols-3">
            {STEPS.map((s, i) => (
              <Reveal key={s.n} delay={i * 100}>
                <div>
                  <span className="text-5xl font-semibold text-ink-200">{s.n}</span>
                  <h3 className="mt-2 font-semibold text-navy-900">{s.t}</h3>
                  <p className="mt-2 text-sm leading-relaxed text-ink-600">{s.d}</p>
                </div>
              </Reveal>
            ))}
          </div>
        </section>

        {/* ---------------- Contact ---------------- */}
        <section id="contact" className="bg-navy-900 py-20">
          <div className="mx-auto max-w-3xl px-5 text-center">
            <Reveal>
              <h2 className="text-3xl font-semibold tracking-tight text-white">
                Book a free trial class
              </h2>
              <p className="mx-auto mt-4 max-w-lg text-[15px] leading-relaxed text-navy-200">
                Tell us your child&apos;s grade and the subjects they need. We
                will suggest a tutor and a timing that works for you.
              </p>

              <div className="mt-9 flex flex-col items-center justify-center gap-3 sm:flex-row">
                <a
                  href={whatsappLink()}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex h-12 w-full items-center justify-center gap-2 rounded-lg bg-gold-500 px-6 text-sm font-semibold text-navy-950 transition-all duration-150 hover:-translate-y-px hover:bg-gold-400 sm:w-auto"
                >
                  <svg className="h-4 w-4" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
                    <path d="M17.5 14.4c-.3-.2-1.7-.9-2-1-.3-.1-.5-.1-.7.1-.2.3-.7 1-.9 1.2-.2.2-.3.2-.6.1-1.7-.9-2.9-1.6-4-3.6-.3-.5.3-.5.8-1.5.1-.2 0-.4 0-.5s-.7-1.6-.9-2.2c-.2-.6-.5-.5-.7-.5h-.6c-.2 0-.5.1-.8.4-.3.3-1 1-1 2.5s1.1 2.9 1.2 3.1c.2.2 2.1 3.2 5.1 4.5 1.9.8 2.6.9 3.5.7.6-.1 1.7-.7 1.9-1.3.2-.7.2-1.2.2-1.3-.1-.2-.3-.2-.5-.3zM12 2a10 10 0 0 0-8.6 15.1L2 22l5-1.3A10 10 0 1 0 12 2zm0 18.2c-1.5 0-3-.4-4.3-1.2l-.3-.2-3 .8.8-2.9-.2-.3A8.2 8.2 0 1 1 12 20.2z" />
                  </svg>
                  WhatsApp us
                </a>
                <a
                  href={`tel:${site.phone.e164}`}
                  className="inline-flex h-12 w-full items-center justify-center rounded-lg border border-white/20 px-6 text-sm font-medium text-white transition-all duration-150 hover:-translate-y-px hover:bg-white/10 sm:w-auto"
                >
                  Call {site.phone.display}
                </a>
              </div>

              <p className="mt-7 text-sm text-navy-300">
                <a
                  href={`mailto:${site.email}`}
                  className="underline decoration-navy-500 underline-offset-4 transition-colors hover:text-white"
                >
                  {site.email}
                </a>
                <span className="mx-2.5 text-navy-500">·</span>
                {site.address.full}
              </p>
            </Reveal>
          </div>
        </section>
      </main>

      <footer className="border-t border-ink-200 bg-white py-10">
        <div className="mx-auto max-w-6xl px-5">
          <div className="flex flex-col gap-6 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <span className="font-semibold text-navy-900">
                SS <span className="text-gold-600">TUITIONS</span>
              </span>
              <p className="mt-2 text-sm text-ink-500">{site.address.full}</p>
            </div>

            <div className="flex flex-col gap-2 text-sm text-ink-600 sm:items-end">
              <a href={`tel:${site.phone.e164}`} className="hover:text-navy-900">
                {site.phone.display}
              </a>
              <a href={`mailto:${site.email}`} className="hover:text-navy-900">
                {site.email}
              </a>
              {site.social.instagram && (
                <a
                  href={site.social.instagram.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1.5 hover:text-navy-900"
                >
                  <svg className="h-4 w-4" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
                    <path d="M12 2c2.7 0 3.1 0 4.1.06 1 .05 1.7.2 2.3.44a4.6 4.6 0 0 1 1.7 1.1 4.6 4.6 0 0 1 1.1 1.7c.24.6.4 1.3.44 2.3.05 1 .06 1.4.06 4.1s0 3.1-.06 4.1c-.05 1-.2 1.7-.44 2.3a4.9 4.9 0 0 1-2.8 2.8c-.6.24-1.3.4-2.3.44-1 .05-1.4.06-4.1.06s-3.1 0-4.1-.06c-1-.05-1.7-.2-2.3-.44a4.9 4.9 0 0 1-2.8-2.8c-.24-.6-.4-1.3-.44-2.3C2.01 15.1 2 14.7 2 12s0-3.1.06-4.1c.05-1 .2-1.7.44-2.3a4.6 4.6 0 0 1 1.1-1.7 4.6 4.6 0 0 1 1.7-1.1c.6-.24 1.3-.4 2.3-.44C8.9 2.01 9.3 2 12 2Zm0 1.8c-2.67 0-2.99.01-4 .06-.78.03-1.2.16-1.48.27-.37.14-.64.32-.92.6-.28.28-.46.55-.6.92-.11.28-.24.7-.27 1.48-.05 1.01-.06 1.33-.06 4s.01 2.99.06 4c.03.78.16 1.2.27 1.48.14.37.32.64.6.92.28.28.55.46.92.6.28.11.7.24 1.48.27 1.01.05 1.33.06 4 .06s2.99-.01 4-.06c.78-.03 1.2-.16 1.48-.27.37-.14.64-.32.92-.6.28-.28.46-.55.6-.92.11-.28.24-.7.27-1.48.05-1.01.06-1.33.06-4s-.01-2.99-.06-4c-.03-.78-.16-1.2-.27-1.48a2.5 2.5 0 0 0-.6-.92 2.5 2.5 0 0 0-.92-.6c-.28-.11-.7-.24-1.48-.27-1.01-.05-1.33-.06-4-.06Zm0 3.06a5.14 5.14 0 1 1 0 10.28 5.14 5.14 0 0 1 0-10.28Zm0 1.8a3.34 3.34 0 1 0 0 6.68 3.34 3.34 0 0 0 0-6.68Zm5.34-3.2a1.2 1.2 0 1 1 0 2.4 1.2 1.2 0 0 1 0-2.4Z" />
                  </svg>
                  @{site.social.instagram.handle}
                </a>
              )}
            </div>
          </div>

          <p className="mt-8 border-t border-ink-200 pt-6 text-center text-sm text-ink-500">
            © {new Date().getFullYear()} SS Tuitions. All rights reserved.
          </p>
        </div>
      </footer>
    </>
  );
}
