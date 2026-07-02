import { useEffect, useMemo, useState } from 'react';
import { createPortal } from 'react-dom';
import { AnimatePresence, motion } from 'framer-motion';
import { ArrowLeft, ArrowRight, Check, X } from 'lucide-react';
import { useAppStore } from '../../store/app.js';
import { TOURS } from './tours/index.js';
import { POPOVER_SIZE, placePopover } from './popover-position.js';
import { useTargetRect } from './use-target-rect.js';

const SPOT_PADDING = 8;

export function TourSpotlight() {
  const activeTour = useAppStore((s) => s.activeTour);
  const stepIndex = useAppStore((s) => s.tourStepIndex);
  const next = useAppStore((s) => s.nextTourStep);
  const prev = useAppStore((s) => s.prevTourStep);
  const stop = useAppStore((s) => s.stopTour);

  const tour = activeTour ? TOURS[activeTour] : null;
  const step = tour?.steps[stepIndex];
  const totalSteps = tour?.steps.length ?? 0;
  const isLast = !!tour && stepIndex >= totalSteps - 1;

  const padding = step?.padding ?? SPOT_PADDING;
  const rect = useTargetRect(step?.target, !!step);

  const [viewport, setViewport] = useState(() => ({
    width: typeof window === 'undefined' ? 1280 : window.innerWidth,
    height: typeof window === 'undefined' ? 720 : window.innerHeight,
  }));

  useEffect(() => {
    const onResize = () => setViewport({ width: window.innerWidth, height: window.innerHeight });
    window.addEventListener('resize', onResize);
    return () => window.removeEventListener('resize', onResize);
  }, []);

  useEffect(() => {
    step?.onEnter?.();
    return () => step?.onLeave?.();
  }, [step]);

  // ESC quits, arrows navigate. Captured at window level so input focus
  // inside a tour target doesn't swallow them.
  useEffect(() => {
    if (!activeTour) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.preventDefault();
        stop(false);
      } else if (e.key === 'ArrowRight') {
        e.preventDefault();
        if (isLast) stop(true);
        else next();
      } else if (e.key === 'ArrowLeft') {
        e.preventDefault();
        prev();
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [activeTour, isLast, next, prev, stop]);

  const popover = useMemo(
    () => placePopover(rect, step?.placement, viewport),
    [rect, step?.placement, viewport],
  );

  if (!tour || !step) return null;

  const spot = rect
    ? {
        top: rect.top - padding,
        left: rect.left - padding,
        width: rect.width + padding * 2,
        height: rect.height + padding * 2,
      }
    : null;

  return createPortal(
    <AnimatePresence>
      <motion.div
        key="tour-overlay"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        transition={{ duration: 0.2 }}
        className="fixed inset-0 z-[100] pointer-events-none"
        aria-modal="true"
        role="dialog"
        aria-label={`${tour.title} — step ${stepIndex + 1} of ${totalSteps}`}
      >
        <SpotlightMask spot={spot} viewport={viewport} onClick={() => stop(false)} />
        {spot && (
          <motion.div
            layout
            transition={{ type: 'spring', stiffness: 260, damping: 28 }}
            className="absolute rounded-xl pointer-events-none"
            style={{
              top: spot.top,
              left: spot.left,
              width: spot.width,
              height: spot.height,
              boxShadow:
                '0 0 0 2px rgb(var(--accent) / 0.55), 0 0 0 6px rgb(var(--accent) / 0.18), 0 18px 60px -10px rgb(var(--accent) / 0.45)',
            }}
          />
        )}
        <motion.div
          key={`step-${tour.id}-${step.id}`}
          initial={{ opacity: 0, y: 8, scale: 0.98 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: -4 }}
          transition={{ duration: 0.22, ease: [0.22, 1, 0.36, 1] }}
          className="absolute pointer-events-auto rounded-xl border shadow-2xl"
          style={{
            top: popover.top,
            left: popover.left,
            width: POPOVER_SIZE.width,
            background: 'rgb(var(--surface-elevated))',
            borderColor: 'rgb(var(--border))',
            color: 'rgb(var(--text))',
          }}
        >
          <div
            className="flex items-center justify-between px-4 pt-3.5 pb-1.5"
            style={{ color: 'rgb(var(--text-dim))' }}
          >
            <span className="text-[10px] font-mono uppercase tracking-wide">
              {tour.title} · {stepIndex + 1}/{totalSteps}
            </span>
            <button
              onClick={() => stop(false)}
              className="btn-icon w-6 h-6"
              aria-label="Close tour"
              title="Close (Esc)"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
          <div className="px-4 pb-3">
            <h3 className="text-[14px] font-semibold mb-1.5">{step.title}</h3>
            <p
              className="text-[12.5px] leading-relaxed"
              style={{ color: 'rgb(var(--text-muted))' }}
            >
              {step.body}
            </p>
          </div>
          <div
            className="flex items-center justify-between px-3 py-2.5 border-t gap-2"
            style={{ borderColor: 'rgb(var(--border-subtle))' }}
          >
            <div className="flex gap-1.5" aria-hidden>
              {tour.steps.map((_, i) => (
                <span
                  key={i}
                  className="h-1 rounded-full transition-all"
                  style={{
                    width: i === stepIndex ? 18 : 6,
                    background: i <= stepIndex ? 'rgb(var(--accent))' : 'rgb(var(--border))',
                  }}
                />
              ))}
            </div>
            <div className="flex items-center gap-1.5">
              <button
                onClick={() => stop(false)}
                className="text-[11px] px-2 py-1 rounded-md hover:bg-surface-2/60 transition-colors"
                style={{ color: 'rgb(var(--text-dim))' }}
              >
                Skip
              </button>
              {stepIndex > 0 && (
                <button onClick={prev} className="btn h-7 px-2.5" aria-label="Previous step">
                  <ArrowLeft className="w-3.5 h-3.5" />
                </button>
              )}
              {isLast ? (
                <button onClick={() => stop(true)} className="btn-primary h-7 px-3">
                  <Check className="w-3.5 h-3.5" />
                  Done
                </button>
              ) : (
                <button onClick={next} className="btn-primary h-7 px-3">
                  Next
                  <ArrowRight className="w-3.5 h-3.5" />
                </button>
              )}
            </div>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>,
    document.body,
  );
}

interface MaskProps {
  spot: { top: number; left: number; width: number; height: number } | null;
  viewport: { width: number; height: number };
  onClick: () => void;
}

// Four dim strips (top / left / right / bottom) around the spot. Leaves the
// target fully visible and click-through, while every strip captures clicks
// outside the highlight to dismiss the tour. We avoid clip-path/SVG masks
// because their cross-browser behaviour with `evenodd` + percentage units is
// inconsistent and was producing a solid blurred overlay instead of a hole.
function SpotlightMask({ spot, viewport, onClick }: MaskProps) {
  const dim = 'rgb(0 0 0 / 0.58)';
  if (!spot) {
    return (
      <button
        type="button"
        aria-label="Dismiss tour"
        onClick={onClick}
        className="absolute inset-0 pointer-events-auto cursor-default"
        style={{ background: dim }}
      />
    );
  }
  const top = Math.max(0, spot.top);
  const bottom = Math.min(viewport.height, spot.top + spot.height);
  const left = Math.max(0, spot.left);
  const right = Math.min(viewport.width, spot.left + spot.width);
  const stripBase = 'absolute pointer-events-auto cursor-default';
  return (
    <>
      <button
        type="button"
        aria-label="Dismiss tour"
        onClick={onClick}
        className={stripBase}
        style={{ top: 0, left: 0, width: viewport.width, height: top, background: dim }}
      />
      <button
        type="button"
        aria-label="Dismiss tour"
        onClick={onClick}
        className={stripBase}
        style={{
          top: bottom,
          left: 0,
          width: viewport.width,
          height: Math.max(0, viewport.height - bottom),
          background: dim,
        }}
      />
      <button
        type="button"
        aria-label="Dismiss tour"
        onClick={onClick}
        className={stripBase}
        style={{
          top,
          left: 0,
          width: left,
          height: Math.max(0, bottom - top),
          background: dim,
        }}
      />
      <button
        type="button"
        aria-label="Dismiss tour"
        onClick={onClick}
        className={stripBase}
        style={{
          top,
          left: right,
          width: Math.max(0, viewport.width - right),
          height: Math.max(0, bottom - top),
          background: dim,
        }}
      />
    </>
  );
}
