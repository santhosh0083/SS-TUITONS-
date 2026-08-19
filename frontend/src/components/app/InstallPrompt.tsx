"use client";

import { useEffect, useState, useSyncExternalStore } from "react";

/**
 * Offers to install the app.
 *
 * Without this, installing is a browser menu item most people never open, so
 * the app would exist and nobody would have it. Android fires an event we can
 * turn into a real button; iOS has no such API, so Safari users get the two
 * steps written out instead.
 *
 * Dismissal is remembered. Someone who says no is not asked again -- a banner
 * that keeps coming back is how an app teaches people to ignore it.
 */

const DISMISSED_KEY = "ss-install-dismissed";

interface InstallEvent extends Event {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed" }>;
}

function isIos(): boolean {
  if (typeof navigator === "undefined") return false;
  return (
    /iphone|ipad|ipod/i.test(navigator.userAgent) ||
    // iPadOS 13+ reports as a Mac, and is only distinguishable by touch.
    (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1)
  );
}

function isInstalled(): boolean {
  if (typeof window === "undefined") return false;
  return (
    window.matchMedia("(display-mode: standalone)").matches ||
    // Safari's own flag, which predates the standard media query.
    (window.navigator as Navigator & { standalone?: boolean }).standalone === true
  );
}

/**
 * Whether we are past hydration.
 *
 * Everything this component decides on -- platform, installed state, a
 * previous dismissal -- lives in the browser and is unknowable on the server.
 * Reading it during render would make the server and client markup disagree;
 * setting it from an effect makes React re-render immediately for no reason.
 * This is the case useSyncExternalStore exists for: a value that is one thing
 * on the server and another in the browser, resolved once at hydration.
 */
const subscribe = () => () => {};

export function InstallPrompt() {
  const hydrated = useSyncExternalStore(
    subscribe,
    () => true,
    () => false,
  );
  const [event, setEvent] = useState<InstallEvent | null>(null);
  const [dismissed, setDismissed] = useState(false);

  useEffect(() => {
    const onPrompt = (e: Event) => {
      // Chrome shows its own bar unless this is cancelled, and that bar
      // appears at the worst moment with no say from us.
      e.preventDefault();
      setEvent(e as InstallEvent);
    };
    window.addEventListener("beforeinstallprompt", onPrompt);
    return () => window.removeEventListener("beforeinstallprompt", onPrompt);
  }, []);

  function dismiss() {
    localStorage.setItem(DISMISSED_KEY, "1");
    setDismissed(true);
    setEvent(null);
  }

  async function install() {
    if (!event) return;
    await event.prompt();
    await event.userChoice;
    // The event can only be used once, whatever the answer.
    setEvent(null);
  }

  if (!hydrated) return null;
  if (dismissed || localStorage.getItem(DISMISSED_KEY)) return null;
  if (isInstalled()) return null;

  // iOS has no install API at all, so Safari users get the two steps spelled
  // out instead of a button that cannot exist.
  const showIosHelp = isIos();
  if (!event && !showIosHelp) return null;

  return (
    <div className="fixed inset-x-0 bottom-0 z-40 p-3 pb-[max(0.75rem,env(safe-area-inset-bottom))]">
      <div className="mx-auto flex max-w-md items-center gap-3 rounded-xl border border-ink-200 bg-white p-3 shadow-[var(--shadow-card)]">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src="/icons/icon-192.png"
          alt=""
          width={40}
          height={40}
          className="h-10 w-10 shrink-0 rounded-lg"
        />
        <div className="min-w-0 flex-1">
          <p className="text-sm font-semibold text-navy-900">
            Install SS Tuitions
          </p>
          <p className="mt-0.5 text-xs leading-snug text-ink-500">
            {showIosHelp
              ? "Tap Share, then “Add to Home Screen”."
              : "Get it on your home screen, like any other app."}
          </p>
        </div>
        {event && (
          <button
            type="button"
            onClick={install}
            className="shrink-0 rounded-lg bg-navy-900 px-3.5 py-2 text-sm font-semibold text-white transition-colors hover:bg-navy-800"
          >
            Install
          </button>
        )}
        <button
          type="button"
          onClick={dismiss}
          aria-label="Not now"
          className="shrink-0 rounded-lg p-2 text-ink-400 transition-colors hover:bg-ink-50 hover:text-ink-600"
        >
          <svg
            className="h-4 w-4"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            aria-hidden="true"
          >
            <path d="M18 6 6 18M6 6l12 12" />
          </svg>
        </button>
      </div>
    </div>
  );
}
