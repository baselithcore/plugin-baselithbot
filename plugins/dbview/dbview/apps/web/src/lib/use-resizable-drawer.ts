import { useCallback, useEffect, useRef, useState } from 'react';

interface Options {
  storageKey: string;
  defaultWidth?: number;
  minWidth?: number;
  maxWidth?: number;
}

interface Result {
  width: number;
  isResizing: boolean;
  isExpanded: boolean;
  toggleExpanded: () => void;
  handleProps: {
    onPointerDown: (e: React.PointerEvent<HTMLDivElement>) => void;
    onDoubleClick: () => void;
    onKeyDown: (e: React.KeyboardEvent<HTMLDivElement>) => void;
  };
}

const DEFAULT = 520;
const MIN = 360;

function readStored(key: string, fallback: number): number {
  if (typeof window === 'undefined') return fallback;
  const raw = window.localStorage.getItem(key);
  if (!raw) return fallback;
  const n = Number(raw);
  return Number.isFinite(n) && n > 0 ? n : fallback;
}

function clamp(value: number, min: number, max: number): number {
  return Math.min(Math.max(value, min), max);
}

function viewportMax(maxWidth: number): number {
  if (typeof window === 'undefined') return maxWidth;
  return Math.min(maxWidth, Math.round(window.innerWidth * 0.95));
}

/**
 * Drag handle anchored on the LEFT edge of a right-anchored drawer.
 * New width = viewport - pointer.clientX (drag left → wider).
 */
export function useResizableDrawer({
  storageKey,
  defaultWidth = DEFAULT,
  minWidth = MIN,
  maxWidth = 2400,
}: Options): Result {
  const [width, setWidth] = useState<number>(() => readStored(storageKey, defaultWidth));
  const [isResizing, setIsResizing] = useState(false);
  const frame = useRef<number | null>(null);
  const pending = useRef<number | null>(null);

  useEffect(() => {
    setWidth((w) => clamp(w, minWidth, viewportMax(maxWidth)));
    const onResize = () => setWidth((w) => clamp(w, minWidth, viewportMax(maxWidth)));
    window.addEventListener('resize', onResize);
    return () => window.removeEventListener('resize', onResize);
  }, [minWidth, maxWidth]);

  useEffect(() => {
    try {
      window.localStorage.setItem(storageKey, String(width));
    } catch {
      // storage unavailable; ignore
    }
  }, [storageKey, width]);

  const applyPending = useCallback(() => {
    frame.current = null;
    if (pending.current == null) return;
    setWidth(clamp(pending.current, minWidth, viewportMax(maxWidth)));
    pending.current = null;
  }, [minWidth, maxWidth]);

  const onPointerDown = useCallback(
    (e: React.PointerEvent<HTMLDivElement>) => {
      e.preventDefault();
      const target = e.currentTarget;
      target.setPointerCapture(e.pointerId);
      setIsResizing(true);
      const prevBodyCursor = document.body.style.cursor;
      const prevUserSelect = document.body.style.userSelect;
      document.body.style.cursor = 'col-resize';
      document.body.style.userSelect = 'none';

      const onMove = (ev: PointerEvent) => {
        pending.current = window.innerWidth - ev.clientX;
        if (frame.current == null) {
          frame.current = requestAnimationFrame(applyPending);
        }
      };
      const onUp = (ev: PointerEvent) => {
        try {
          target.releasePointerCapture(ev.pointerId);
        } catch {
          // capture already released; ignore
        }
        target.removeEventListener('pointermove', onMove);
        target.removeEventListener('pointerup', onUp);
        target.removeEventListener('pointercancel', onUp);
        if (frame.current != null) {
          cancelAnimationFrame(frame.current);
          frame.current = null;
        }
        if (pending.current != null) {
          setWidth(clamp(pending.current, minWidth, viewportMax(maxWidth)));
          pending.current = null;
        }
        document.body.style.cursor = prevBodyCursor;
        document.body.style.userSelect = prevUserSelect;
        setIsResizing(false);
      };
      target.addEventListener('pointermove', onMove);
      target.addEventListener('pointerup', onUp);
      target.addEventListener('pointercancel', onUp);
    },
    [applyPending, minWidth, maxWidth],
  );

  const onDoubleClick = useCallback(() => {
    setWidth(clamp(defaultWidth, minWidth, viewportMax(maxWidth)));
  }, [defaultWidth, minWidth, maxWidth]);

  const lastCompact = useRef<number>(defaultWidth);
  const isExpanded = width >= viewportMax(maxWidth) - 1;
  const toggleExpanded = useCallback(() => {
    setWidth((w) => {
      const max = viewportMax(maxWidth);
      if (w >= max - 1) {
        return clamp(lastCompact.current, minWidth, max);
      }
      lastCompact.current = w;
      return max;
    });
  }, [minWidth, maxWidth]);

  const onKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLDivElement>) => {
      const step = e.shiftKey ? 64 : 16;
      if (e.key === 'ArrowLeft') {
        e.preventDefault();
        setWidth((w) => clamp(w + step, minWidth, viewportMax(maxWidth)));
      } else if (e.key === 'ArrowRight') {
        e.preventDefault();
        setWidth((w) => clamp(w - step, minWidth, viewportMax(maxWidth)));
      } else if (e.key === 'Home') {
        e.preventDefault();
        setWidth(viewportMax(maxWidth));
      } else if (e.key === 'End') {
        e.preventDefault();
        setWidth(minWidth);
      }
    },
    [minWidth, maxWidth],
  );

  return {
    width,
    isResizing,
    isExpanded,
    toggleExpanded,
    handleProps: { onPointerDown, onDoubleClick, onKeyDown },
  };
}
