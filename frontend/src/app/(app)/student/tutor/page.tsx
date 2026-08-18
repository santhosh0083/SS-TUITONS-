"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { Button } from "@/components/ui/Button";
import { ApiError, apiFetch } from "@/lib/api";

interface Status {
  available: boolean;
  reason: string | null;
}

interface HistoryMessage {
  role: string;
  content: string;
  at: string;
}

interface AskResponse {
  answer: string;
  questions_used_today: number;
  daily_limit: number;
}

const STARTERS = [
  "I'm stuck on a projectile motion problem",
  "Explain the difference between SN1 and SN2",
  "How do I start an integration by parts question?",
  "I got this sum wrong — can you help me see why?",
];

export default function AITutorPage() {
  const [status, setStatus] = useState<Status | null>(null);
  const [messages, setMessages] = useState<HistoryMessage[]>([]);
  const [draft, setDraft] = useState("");
  const [thinking, setThinking] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [usage, setUsage] = useState<{ used: number; limit: number } | null>(null);

  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    apiFetch<Status>("/ai/status")
      .then((s) => {
        setStatus(s);
        if (s.available) {
          apiFetch<HistoryMessage[]>("/ai/history")
            .then(setMessages)
            .catch(() => setMessages([]));
        }
      })
      .catch(() => setStatus({ available: false, reason: "Unavailable." }));
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, thinking]);

  const send = useCallback(
    async (text: string) => {
      const question = text.trim();
      if (!question || thinking) return;

      setError(null);
      setDraft("");
      setMessages((m) => [
        ...m,
        { role: "user", content: question, at: new Date().toISOString() },
      ]);
      setThinking(true);

      try {
        const res = await apiFetch<AskResponse>("/ai/ask", {
          method: "POST",
          body: { question },
        });
        setMessages((m) => [
          ...m,
          { role: "assistant", content: res.answer, at: new Date().toISOString() },
        ]);
        setUsage({ used: res.questions_used_today, limit: res.daily_limit });
      } catch (err) {
        setError(
          err instanceof ApiError ? err.message : "Could not reach the tutor.",
        );
      } finally {
        setThinking(false);
      }
    },
    [thinking],
  );

  // ---- Not switched on ----
  if (status && !status.available) {
    return (
      <div className="mx-auto max-w-2xl">
        <h1 className="text-2xl font-semibold tracking-tight text-navy-900">
          AI Tutor
        </h1>
        <div className="mt-8 rounded-xl border border-dashed border-ink-300 bg-white px-6 py-14 text-center">
          <span className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-navy-50">
            <svg
              className="h-6 w-6 text-navy-600"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.5"
              aria-hidden="true"
            >
              <path d="M12 3 2 8l10 5 10-5-10-5Zm0 9.5L5 9v4.5c0 2 3.1 3.5 7 3.5s7-1.5 7-3.5V9" />
            </svg>
          </span>
          <h2 className="mt-4 font-semibold text-navy-900">
            The AI tutor is not available yet
          </h2>
          <p className="mx-auto mt-1.5 max-w-sm text-sm text-ink-500">
            {status.reason} Your SS Tuitions tutor can help in the meantime.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="mx-auto flex h-[calc(100vh-8rem)] max-w-2xl flex-col">
      <header className="shrink-0">
        <h1 className="text-2xl font-semibold tracking-tight text-navy-900">
          AI Tutor
        </h1>
        <p className="mt-1 text-sm text-ink-500">
          Stuck on something? I&apos;ll help you work it out — not just hand you
          the answer.
        </p>
      </header>

      <div className="mt-6 flex-1 space-y-4 overflow-y-auto rounded-xl border border-ink-200 bg-white p-5">
        {!status && (
          <div className="space-y-3">
            {[0, 1].map((i) => (
              <div key={i} className="h-14 animate-pulse rounded-xl bg-ink-100" />
            ))}
          </div>
        )}

        {status?.available && messages.length === 0 && (
          <div className="py-6 text-center">
            <p className="text-sm text-ink-600">
              Ask me anything about your subjects.
            </p>
            <div className="mt-5 grid gap-2">
              {STARTERS.map((s) => (
                <button
                  key={s}
                  type="button"
                  onClick={() => send(s)}
                  className="rounded-lg border border-ink-200 px-4 py-2.5 text-left text-sm text-ink-700 transition-all hover:-translate-y-px hover:border-navy-300 hover:bg-ink-50"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((m, i) => (
          <div
            key={`${m.at}-${i}`}
            className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}
          >
            <div
              className={[
                "max-w-[85%] animate-[var(--animate-fade-up)] rounded-2xl px-4 py-3",
                m.role === "user"
                  ? "rounded-br-sm bg-navy-900 text-white"
                  : "rounded-bl-sm bg-ink-100 text-ink-900",
              ].join(" ")}
            >
              <p className="whitespace-pre-wrap break-words text-sm leading-relaxed">
                {m.content}
              </p>
            </div>
          </div>
        ))}

        {thinking && (
          <div className="flex justify-start">
            <div className="rounded-2xl rounded-bl-sm bg-ink-100 px-4 py-3">
              <span className="flex gap-1" aria-label="Tutor is thinking">
                {[0, 1, 2].map((i) => (
                  <span
                    key={i}
                    className="h-1.5 w-1.5 animate-bounce rounded-full bg-ink-400"
                    style={{ animationDelay: `${i * 140}ms` }}
                  />
                ))}
              </span>
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {error && (
        <div
          role="alert"
          className="mt-3 shrink-0 rounded-lg border border-danger-500/25 bg-danger-50 px-3.5 py-3 text-sm text-danger-700"
        >
          {error}
        </div>
      )}

      <form
        onSubmit={(e) => {
          e.preventDefault();
          void send(draft);
        }}
        className="mt-3 flex shrink-0 items-end gap-2"
      >
        <label htmlFor="q" className="sr-only">
          Your question
        </label>
        <textarea
          id="q"
          rows={1}
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              void send(draft);
            }
          }}
          maxLength={2000}
          placeholder="Type your question…"
          disabled={thinking || !status?.available}
          className="max-h-32 min-h-[2.75rem] flex-1 resize-y rounded-lg border border-ink-300 px-3.5 py-2.5 text-sm text-ink-900 placeholder:text-ink-400 focus:border-navy-500 focus:outline-none focus:ring-2 focus:ring-navy-500/25"
        />
        <Button
          type="submit"
          loading={thinking}
          disabled={!draft.trim() || !status?.available}
        >
          Ask
        </Button>
      </form>

      <p className="mt-2 shrink-0 text-xs text-ink-400">
        Your name and contact details are never sent to the AI.
        {usage && ` · ${usage.used} of ${usage.limit} questions used today`}
      </p>
    </div>
  );
}
