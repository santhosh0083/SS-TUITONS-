"use client";

import { useEffect, useRef, useState, type ReactNode } from "react";

interface RevealProps {
  children: ReactNode;
  delay?: number;
  className?: string;
}

/**
 * Fades content up as it scrolls into view.
 *
 * Uses IntersectionObserver rather than a scroll listener, so the browser does
 * the work off the main thread and long pages stay smooth on cheap phones —
 * which is what most students will be using.
 *
 * Reduced motion is handled entirely in CSS: the global
 * `prefers-reduced-motion` rule collapses transition-duration to ~0, so content
 * still appears on intersection, just without the movement. Anything already in
 * the viewport intersects immediately, so nothing is ever stuck invisible.
 */
export function Reveal({ children, delay = 0, className = "" }: RevealProps) {
  const ref = useRef<HTMLDivElement>(null);
  // Browsers without IntersectionObserver skip the animation and render
  // visible from the start, rather than being left with invisible content.
  const [visible, setVisible] = useState(
    () => typeof window !== "undefined" && !("IntersectionObserver" in window),
  );

  useEffect(() => {
    const node = ref.current;
    if (!node || !("IntersectionObserver" in window)) return;

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setVisible(true);
          observer.disconnect(); // animate once; never re-run on scroll back
        }
      },
      { threshold: 0.12, rootMargin: "0px 0px -40px 0px" },
    );

    observer.observe(node);
    return () => observer.disconnect();
  }, []);

  return (
    <div
      ref={ref}
      className={className}
      style={{
        opacity: visible ? 1 : 0,
        transform: visible ? "translateY(0)" : "translateY(16px)",
        transition: `opacity 0.55s var(--ease-out-soft) ${delay}ms, transform 0.55s var(--ease-out-soft) ${delay}ms`,
      }}
    >
      {children}
    </div>
  );
}
