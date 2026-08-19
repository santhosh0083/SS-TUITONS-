"use client";

import { useEffect } from "react";

/**
 * Registers the service worker, which is what makes the site installable and
 * gives it an offline page.
 *
 * Registration is deferred until after load. A service worker install competes
 * for bandwidth with the page itself, and on the phone connections this app is
 * used over, racing them makes the first visit slower for no benefit.
 *
 * Development is skipped entirely: a worker caching a dev build produces
 * changes that will not appear until the cache is cleared by hand, which wastes
 * more time than the feature saves.
 */
export function ServiceWorker() {
  useEffect(() => {
    if (process.env.NODE_ENV !== "production") return;
    if (!("serviceWorker" in navigator)) return;

    const register = () => {
      navigator.serviceWorker.register("/sw.js").catch(() => {
        // An unregistered worker costs an offline page, not the app. There is
        // nothing useful to show a parent about it.
      });
    };

    if (document.readyState === "complete") {
      register();
    } else {
      window.addEventListener("load", register, { once: true });
      return () => window.removeEventListener("load", register);
    }
  }, []);

  return null;
}
