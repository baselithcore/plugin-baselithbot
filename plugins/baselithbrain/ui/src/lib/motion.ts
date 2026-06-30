// Shared Motion variants + transitions. One source of truth so every surface
// eases the same way. Calm and quick — short fades and small offsets, no bouncy
// springs. Reduced-motion is respected by Motion automatically.
import type { Transition, Variants } from 'motion/react';

/** Standard quick ease for panels / layout. */
export const spring: Transition = { duration: 0.16, ease: [0.22, 1, 0.36, 1] };

/** Slightly softer ease for large overlays. */
export const springSoft: Transition = { duration: 0.2, ease: [0.22, 1, 0.36, 1] };

/** Quick eased tween for opacity-only fades. */
export const ease: Transition = { duration: 0.14, ease: [0.22, 1, 0.36, 1] };

/** Fade + small lift, used for modals/cards. */
export const popVariants: Variants = {
  hidden: { opacity: 0, y: 4 },
  show: { opacity: 1, y: 0, transition: spring },
  exit: { opacity: 0, y: 3, transition: ease },
};

/** Slide-in drawer from the right edge. */
export const drawerVariants: Variants = {
  hidden: { x: '100%' },
  show: { x: 0, transition: springSoft },
  exit: { x: '100%', transition: { duration: 0.16, ease: [0.4, 0, 1, 1] } },
};

/** Backdrop fade. */
export const backdropVariants: Variants = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: ease },
  exit: { opacity: 0, transition: ease },
};

/** Staggered list container — children animate in sequence (very subtle). */
export const listVariants: Variants = {
  hidden: {},
  show: { transition: { staggerChildren: 0.012 } },
};

/** Single list item fading into place. */
export const itemVariants: Variants = {
  hidden: { opacity: 0, y: 2 },
  show: { opacity: 1, y: 0, transition: { duration: 0.14, ease: [0.22, 1, 0.36, 1] } },
};

/** Cross-fade for the active note swap in the editor pane. */
export const pageVariants: Variants = {
  hidden: { opacity: 0, y: 4 },
  show: { opacity: 1, y: 0, transition: { duration: 0.16, ease: [0.22, 1, 0.36, 1] } },
  exit: { opacity: 0, transition: { duration: 0.1 } },
};
