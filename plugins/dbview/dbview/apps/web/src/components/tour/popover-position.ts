import type { StepPlacement } from './types.js';
import type { TargetRect } from './use-target-rect.js';

interface ViewportSize {
  width: number;
  height: number;
}

export interface PopoverPlacement {
  top: number;
  left: number;
  arrow: StepPlacement;
}

const GAP = 14;
const POPOVER_WIDTH = 360;
const POPOVER_HEIGHT_ESTIMATE = 180;
const EDGE_PAD = 16;

// Picks a side that fits within the viewport. Falls back to `bottom` if
// nothing fits to keep the popover on-screen.
export function placePopover(
  rect: TargetRect | null,
  preferred: StepPlacement | undefined,
  viewport: ViewportSize
): PopoverPlacement {
  if (!rect || preferred === 'center') {
    return {
      top: viewport.height / 2 - POPOVER_HEIGHT_ESTIMATE / 2,
      left: viewport.width / 2 - POPOVER_WIDTH / 2,
      arrow: 'center',
    };
  }

  const candidates: StepPlacement[] = preferred
    ? [preferred, 'bottom', 'top', 'right', 'left']
    : ['bottom', 'top', 'right', 'left'];

  for (const side of candidates) {
    const pos = positionFor(rect, side);
    if (fitsInViewport(pos, viewport)) {
      return { ...pos, arrow: side };
    }
  }

  const fallback = positionFor(rect, 'bottom');
  return {
    top: clamp(fallback.top, EDGE_PAD, viewport.height - POPOVER_HEIGHT_ESTIMATE - EDGE_PAD),
    left: clamp(fallback.left, EDGE_PAD, viewport.width - POPOVER_WIDTH - EDGE_PAD),
    arrow: 'bottom',
  };
}

function positionFor(rect: TargetRect, side: StepPlacement): { top: number; left: number } {
  const centerX = rect.left + rect.width / 2 - POPOVER_WIDTH / 2;
  const centerY = rect.top + rect.height / 2 - POPOVER_HEIGHT_ESTIMATE / 2;
  switch (side) {
    case 'top':
      return { top: rect.top - POPOVER_HEIGHT_ESTIMATE - GAP, left: centerX };
    case 'bottom':
      return { top: rect.top + rect.height + GAP, left: centerX };
    case 'left':
      return { top: centerY, left: rect.left - POPOVER_WIDTH - GAP };
    case 'right':
      return { top: centerY, left: rect.left + rect.width + GAP };
    default:
      return { top: rect.top + rect.height + GAP, left: centerX };
  }
}

function fitsInViewport(pos: { top: number; left: number }, v: ViewportSize): boolean {
  return (
    pos.top >= EDGE_PAD &&
    pos.left >= EDGE_PAD &&
    pos.top + POPOVER_HEIGHT_ESTIMATE <= v.height - EDGE_PAD &&
    pos.left + POPOVER_WIDTH <= v.width - EDGE_PAD
  );
}

function clamp(v: number, min: number, max: number): number {
  return Math.min(Math.max(v, min), max);
}

export const POPOVER_SIZE = { width: POPOVER_WIDTH };
