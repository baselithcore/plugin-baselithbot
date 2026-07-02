import { useEffect, useState } from 'react';

export interface TargetRect {
  top: number;
  left: number;
  width: number;
  height: number;
}

// Tracks the bounding rect of a DOM element matching `selector`. Re-measures
// on resize / scroll / animation frame so the spotlight follows layout shifts
// caused by collapsing panels or expanding sections during the tour.
export function useTargetRect(selector: string | undefined, active: boolean): TargetRect | null {
  const [rect, setRect] = useState<TargetRect | null>(null);

  useEffect(() => {
    if (!active || !selector) {
      setRect(null);
      return;
    }
    let raf = 0;
    let lastSerialized = '';

    const measure = () => {
      const el = document.querySelector<HTMLElement>(selector);
      if (!el) {
        raf = requestAnimationFrame(measure);
        return;
      }
      const r = el.getBoundingClientRect();
      const next: TargetRect = {
        top: r.top,
        left: r.left,
        width: r.width,
        height: r.height,
      };
      const serialized = `${next.top}|${next.left}|${next.width}|${next.height}`;
      if (serialized !== lastSerialized) {
        lastSerialized = serialized;
        setRect(next);
      }
      raf = requestAnimationFrame(measure);
    };

    measure();
    return () => cancelAnimationFrame(raf);
  }, [selector, active]);

  return rect;
}
