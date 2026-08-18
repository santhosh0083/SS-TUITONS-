"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { ApiError, apiFetch } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";

interface Participant {
  id: string;
  name: string;
}

interface Conversation {
  id: string;
  student_id: string;
  student_name: string | null;
  subject_line: string | null;
  participants: Participant[];
  last_message_at: string | null;
  unread_count: number;
}

interface Message {
  id: string;
  sender_id: string;
  sender_name: string;
  body: string;
  sent_at: string;
  is_mine: boolean;
}

/** Polling beats WebSockets here: parent-tutor messages are not chat-speed,
 *  and this needs no persistent connection from the host. */
const POLL_MS = 10_000;

function timeLabel(iso: string): string {
  const d = new Date(iso);
  const today = new Date();
  const sameDay = d.toDateString() === today.toDateString();
  return sameDay
    ? d.toLocaleTimeString("en-IN", { hour: "numeric", minute: "2-digit" })
    : d.toLocaleDateString("en-IN", {
        day: "numeric",
        month: "short",
        hour: "numeric",
        minute: "2-digit",
      });
}

function initials(name: string): string {
  return name
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((w) => w[0]?.toUpperCase())
    .join("");
}

export default function MessagesPage() {
  const { user } = useAuth();
  const isAdmin = user?.is_superadmin || user?.roles.includes("ADMIN");

  const [conversations, setConversations] = useState<Conversation[] | null>(null);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[] | null>(null);
  const [draft, setDraft] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const bottomRef = useRef<HTMLDivElement>(null);

  const loadConversations = useCallback(() => {
    apiFetch<Conversation[]>("/messages")
      .then(setConversations)
      .catch((e) =>
        setError(
          e instanceof ApiError ? e.message : "Could not load conversations.",
        ),
      );
  }, []);

  const loadMessages = useCallback(
    (id: string) => {
      const url = isAdmin
        ? `/messages/${id}?reason=admin+review`
        : `/messages/${id}`;
      apiFetch<Message[]>(url)
        .then(setMessages)
        .catch((e) =>
          setError(
            e instanceof ApiError ? e.message : "Could not open this conversation.",
          ),
        );
    },
    [isAdmin],
  );

  useEffect(loadConversations, [loadConversations]);

  // Poll both the list and the open thread.
  useEffect(() => {
    const timer = setInterval(() => {
      loadConversations();
      if (activeId) loadMessages(activeId);
    }, POLL_MS);
    return () => clearInterval(timer);
  }, [activeId, loadConversations, loadMessages]);

  /** Opening a thread is a user action, so the state change belongs here
   *  rather than in an effect reacting to activeId. Clearing first prevents
   *  the previous conversation's messages flashing under the new header. */
  const openConversation = useCallback(
    (id: string) => {
      setActiveId(id);
      setMessages(null);
      loadMessages(id);
    },
    [loadMessages],
  );

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function handleSend(e: React.FormEvent) {
    e.preventDefault();
    const body = draft.trim();
    if (!body || !activeId) return;

    setSending(true);
    setError(null);
    try {
      const created = await apiFetch<Message>(`/messages/${activeId}`, {
        method: "POST",
        body: { body },
      });
      setMessages((prev) => [...(prev ?? []), created]);
      setDraft("");
      loadConversations();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not send.");
    } finally {
      setSending(false);
    }
  }

  const active = conversations?.find((c) => c.id === activeId) ?? null;

  return (
    <div className="mx-auto max-w-6xl">
      <header>
        <h1 className="text-2xl font-semibold tracking-tight text-navy-900">
          Messages
        </h1>
        <p className="mt-1 text-sm text-ink-500">
          {isAdmin
            ? "Every parent–tutor conversation. Your access is recorded in the audit log."
            : "Private messages. Phone numbers are never shared."}
        </p>
      </header>

      {error && (
        <div
          role="alert"
          className="mt-6 rounded-xl border border-danger-500/25 bg-danger-50 px-4 py-3.5 text-sm text-danger-700"
        >
          {error}
        </div>
      )}

      {/* Loading */}
      {!conversations && !error && (
        <div className="mt-8 grid gap-5 lg:grid-cols-[320px_1fr]">
          <div className="h-96 animate-pulse rounded-xl border border-ink-200 bg-white" />
          <div className="hidden h-96 animate-pulse rounded-xl border border-ink-200 bg-white lg:block" />
        </div>
      )}

      {/* Empty */}
      {conversations?.length === 0 && (
        <div className="mt-8 animate-[var(--animate-fade-up)] rounded-xl border border-dashed border-ink-300 bg-white px-6 py-14 text-center">
          <span className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-navy-50">
            <svg
              className="h-6 w-6 text-navy-600"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.5"
              aria-hidden="true"
            >
              <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2v10Z" />
            </svg>
          </span>
          <h2 className="mt-4 font-semibold text-navy-900">No conversations yet</h2>
          <p className="mx-auto mt-1.5 max-w-sm text-sm text-ink-500">
            {isAdmin
              ? "A conversation is created automatically when you assign a tutor to a student."
              : "Conversations appear once a tutor is assigned."}
          </p>
        </div>
      )}

      {conversations && conversations.length > 0 && (
        <div className="mt-8 grid gap-5 lg:grid-cols-[320px_1fr]">
          {/* ---------- Conversation list ---------- */}
          <aside
            className={[
              "rounded-xl border border-ink-200 bg-white shadow-[var(--shadow-card)]",
              // On mobile the list hides once a thread is open.
              activeId ? "hidden lg:block" : "block",
            ].join(" ")}
          >
            <ul className="divide-y divide-ink-200">
              {conversations.map((c) => (
                <li key={c.id}>
                  <button
                    type="button"
                    onClick={() => openConversation(c.id)}
                    aria-current={c.id === activeId ? "true" : undefined}
                    className={[
                      "flex w-full items-start gap-3 px-4 py-3.5 text-left transition-colors",
                      c.id === activeId ? "bg-navy-50" : "hover:bg-ink-50",
                    ].join(" ")}
                  >
                    <span className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-navy-900 text-xs font-semibold text-white">
                      {initials(c.participants[0]?.name ?? c.student_name ?? "?")}
                    </span>
                    <span className="min-w-0 flex-1">
                      <span className="flex items-center justify-between gap-2">
                        <span className="truncate text-sm font-medium text-ink-900">
                          {c.participants.map((p) => p.name).join(", ") || "—"}
                        </span>
                        {c.unread_count > 0 && (
                          <span className="shrink-0 rounded-full bg-gold-500 px-1.5 py-0.5 text-[11px] font-semibold text-navy-950 tabular-nums">
                            {c.unread_count}
                          </span>
                        )}
                      </span>
                      <span className="mt-0.5 block truncate text-xs text-ink-500">
                        {c.student_name ? `About ${c.student_name}` : "—"}
                        {c.subject_line ? ` · ${c.subject_line}` : ""}
                      </span>
                      {c.last_message_at && (
                        <span className="mt-0.5 block text-[11px] text-ink-400">
                          {timeLabel(c.last_message_at)}
                        </span>
                      )}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          </aside>

          {/* ---------- Thread ---------- */}
          <section
            className={[
              "flex min-h-[28rem] flex-col rounded-xl border border-ink-200 bg-white shadow-[var(--shadow-card)]",
              activeId ? "flex" : "hidden lg:flex",
            ].join(" ")}
          >
            {!active ? (
              <div className="flex flex-1 items-center justify-center p-8 text-center text-sm text-ink-500">
                Select a conversation to read it.
              </div>
            ) : (
              <>
                <header className="flex items-center gap-3 border-b border-ink-200 px-5 py-4">
                  <button
                    type="button"
                    onClick={() => setActiveId(null)}
                    aria-label="Back to conversations"
                    className="lg:hidden"
                  >
                    <svg
                      className="h-5 w-5 text-ink-600"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="1.8"
                      aria-hidden="true"
                    >
                      <path strokeLinecap="round" d="m15 18-6-6 6-6" />
                    </svg>
                  </button>
                  <div className="min-w-0">
                    <p className="truncate font-medium text-navy-900">
                      {active.participants.map((p) => p.name).join(", ")}
                    </p>
                    <p className="truncate text-xs text-ink-500">
                      {active.student_name && `About ${active.student_name}`}
                      {active.subject_line && ` · ${active.subject_line}`}
                    </p>
                  </div>
                </header>

                {isAdmin && (
                  <p className="border-b border-warning-500/25 bg-warning-50 px-5 py-2.5 text-xs text-warning-700">
                    You are viewing as an administrator. This access has been
                    recorded in the audit log.
                  </p>
                )}

                <div className="flex-1 space-y-3 overflow-y-auto px-5 py-5">
                  {!messages && (
                    <div className="space-y-3">
                      {[0, 1, 2].map((i) => (
                        <div
                          key={i}
                          className="h-12 w-2/3 animate-pulse rounded-xl bg-ink-100"
                        />
                      ))}
                    </div>
                  )}

                  {messages?.length === 0 && (
                    <p className="py-10 text-center text-sm text-ink-500">
                      No messages yet. Say hello.
                    </p>
                  )}

                  {messages?.map((m) => (
                    <div
                      key={m.id}
                      className={`flex ${m.is_mine ? "justify-end" : "justify-start"}`}
                    >
                      <div
                        className={[
                          "max-w-[80%] animate-[var(--animate-fade-up)] rounded-2xl px-4 py-2.5",
                          m.is_mine
                            ? "rounded-br-sm bg-navy-900 text-white"
                            : "rounded-bl-sm bg-ink-100 text-ink-900",
                        ].join(" ")}
                      >
                        {!m.is_mine && (
                          <p className="mb-0.5 text-[11px] font-medium text-ink-500">
                            {m.sender_name}
                          </p>
                        )}
                        <p className="whitespace-pre-wrap break-words text-sm leading-relaxed">
                          {m.body}
                        </p>
                        <p
                          className={`mt-1 text-[11px] ${m.is_mine ? "text-navy-300" : "text-ink-400"}`}
                        >
                          {timeLabel(m.sent_at)}
                        </p>
                      </div>
                    </div>
                  ))}
                  <div ref={bottomRef} />
                </div>

                <form
                  onSubmit={handleSend}
                  className="flex items-end gap-2 border-t border-ink-200 p-3"
                >
                  <label htmlFor="draft" className="sr-only">
                    Message
                  </label>
                  <textarea
                    id="draft"
                    value={draft}
                    onChange={(e) => setDraft(e.target.value)}
                    onKeyDown={(e) => {
                      // Enter sends; Shift+Enter makes a new line.
                      if (e.key === "Enter" && !e.shiftKey) {
                        e.preventDefault();
                        void handleSend(e);
                      }
                    }}
                    rows={1}
                    maxLength={5000}
                    placeholder={
                      isAdmin
                        ? "Write a message, or paste the class link…"
                        : "Write a message…"
                    }
                    disabled={sending}
                    className="max-h-32 min-h-[2.75rem] flex-1 resize-y rounded-lg border border-ink-300 px-3.5 py-2.5 text-sm text-ink-900 placeholder:text-ink-400 focus:border-navy-500 focus:outline-none focus:ring-2 focus:ring-navy-500/25"
                  />
                  <button
                    type="submit"
                    disabled={sending || !draft.trim()}
                    className="inline-flex h-11 shrink-0 items-center justify-center rounded-lg bg-navy-900 px-4 text-sm font-medium text-white transition-all hover:-translate-y-px hover:bg-navy-800 disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    Send
                  </button>
                </form>
              </>
            )}
          </section>
        </div>
      )}
    </div>
  );
}
