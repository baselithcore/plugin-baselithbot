import type { Transition, Variants } from 'motion/react';

// Shared Aurora-glass motion vocabulary (mirrors the baselithbrain conventions).
export const spring: Transition = {
  type: 'spring',
  stiffness: 420,
  damping: 34,
  mass: 0.8,
};

export const ease: Transition = { duration: 0.18, ease: [0.22, 1, 0.36, 1] };

export const listVariants: Variants = {
  hidden: {},
  show: { transition: { staggerChildren: 0.04 } },
};

export const itemVariants: Variants = {
  hidden: { opacity: 0, y: 8 },
  show: { opacity: 1, y: 0, transition: spring },
};

export const pageVariants: Variants = {
  hidden: { opacity: 0, y: 6 },
  show: { opacity: 1, y: 0, transition: ease },
  exit: { opacity: 0, y: -6, transition: ease },
};
