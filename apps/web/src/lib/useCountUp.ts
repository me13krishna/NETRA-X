"use client";

import { useEffect, useRef, useState } from "react";

/**
 * Counts a value up from zero when it first arrives.
 *
 * A figure that snaps from "..." to "14" reads as a static template. The same
 * figure counting up reads as a console that just finished querying something,
 * which is what this screen is claiming to be.
 *
 * Driven by requestAnimationFrame rather than a CSS transition because the
 * thing being animated is the *text content*, not a style property.
 *
 * Honours prefers-reduced-motion by landing on the final value immediately --
 * the rest of the interface already does this via a global media query, and a
 * JS-driven animation would otherwise ignore it.
 */
export function useCountUp(target: number | null, durationMs = 900): number {
  const [value, setValue] = useState(0);
  const frame = useRef<number>();
  const startedFrom = useRef(0);

  useEffect(() => {
    if (target === null || Number.isNaN(target)) return;

    const reduced =
      typeof window !== "undefined" &&
      window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;

    if (reduced || durationMs <= 0) {
      setValue(target);
      return;
    }

    const from = startedFrom.current;
    const delta = target - from;
    if (delta === 0) return;

    const t0 = performance.now();
    // easeOutCubic: fast to begin, settling at the end, so the number reads as
    // arriving rather than ticking mechanically.
    const ease = (t: number) => 1 - Math.pow(1 - t, 3);

    const step = (now: number) => {
      const t = Math.min(1, (now - t0) / durationMs);
      const next = Math.round(from + delta * ease(t));
      setValue(next);
      if (t < 1) {
        frame.current = requestAnimationFrame(step);
      } else {
        startedFrom.current = target;
      }
    };

    frame.current = requestAnimationFrame(step);
    return () => {
      if (frame.current) cancelAnimationFrame(frame.current);
    };
  }, [target, durationMs]);

  return value;
}
