import { useEffect, useRef, useState, type RefObject } from 'react';

/**
 * Tracks the pixel size of a container via ResizeObserver. ForceGraph2D/3D
 * require explicit width/height props (canvas does not auto-fit); the
 * container layout is handled by flex/grid CSS, so we measure it.
 */
export function useGraphSize<T extends HTMLElement = HTMLDivElement>(): {
  ref: RefObject<T | null>;
  size: { w: number; h: number };
} {
  const ref = useRef<T | null>(null);
  const [size, setSize] = useState({ w: 0, h: 0 });

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const measure = () => setSize({ w: el.clientWidth, h: el.clientHeight });
    measure();
    const ro = new ResizeObserver(measure);
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  return { ref, size };
}
