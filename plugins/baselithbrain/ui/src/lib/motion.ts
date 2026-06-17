// Shared Motion (framer-motion) variants + transitions. One source of truth so
// every surface eases the same way — premium springs, no jank, reduced-motion
// respected by Motion automatically.
import type { Transition, Variants } from 'motion/react';

/** Snappy premium spring for layout / panels. */
export const spring: Transition = { type: 'spring', stiffness: 420, damping: 34, mass: 0.8 };

/** Softer spring for large overlays. */
export const springSoft: Transition = { type: 'spring', stiffness: 260, damping: 30 };

/** Quick eased tween for opacity-only fades. */
export const ease: Transition = { duration: 0.18, ease: [0.22, 1, 0.36, 1] };

/** Fade + lift, used for modals/cards. */
export const popVariants: Variants = {
  hidden: { opacity: 0, y: 8, scale: 0.97 },
  show: { opacity: 1, y: 0, scale: 1, transition: spring },
  exit: { opacity: 0, y: 6, scale: 0.98, transition: ease },
};

/** Slide-in drawer from the right edge. */
export const drawerVariants: Variants = {
  hidden: { x: '100%', opacity: 0.4 },
  show: { x: 0, opacity: 1, transition: springSoft },
  exit: { x: '100%', opacity: 0.4, transition: { duration: 0.22, ease: [0.4, 0, 1, 1] } },
};

/** Backdrop fade. */
export const backdropVariants: Variants = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: ease },
  exit: { opacity: 0, transition: ease },
};

/** Staggered list container — children animate in sequence. */
export const listVariants: Variants = {
  hidden: {},
  show: { transition: { staggerChildren: 0.025, delayChildren: 0.02 } },
};

/** Single list item rising into place. */
export const itemVariants: Variants = {
  hidden: { opacity: 0, x: -6 },
  show: { opacity: 1, x: 0, transition: { duration: 0.2, ease: [0.22, 1, 0.36, 1] } },
};

/** Cross-fade for the active note swap in the editor pane. */
export const pageVariants: Variants = {
  hidden: { opacity: 0, y: 10 },
  show: { opacity: 1, y: 0, transition: { duration: 0.28, ease: [0.22, 1, 0.36, 1] } },
  exit: { opacity: 0, y: -8, transition: { duration: 0.16 } },
};
