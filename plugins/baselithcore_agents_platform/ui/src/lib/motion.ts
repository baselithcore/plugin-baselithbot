// Shared Motion variants so panels/cards animate consistently across pages.
import type { Variants } from 'motion/react';

export const fadeUp: Variants = {
  hidden: { opacity: 0, y: 12 },
  show: { opacity: 1, y: 0, transition: { duration: 0.35, ease: 'easeOut' } },
};

export const stagger: Variants = {
  hidden: {},
  show: { transition: { staggerChildren: 0.05 } },
};
