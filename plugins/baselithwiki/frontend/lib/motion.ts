// Motion tokens — JS mirror of the --ease-* / --duration-* CSS custom
// properties in index.css. Use these instead of inline cubic-bezier arrays
// so timing/easing stay consistent across framer-motion call sites.
// Calm/technical tone, power-user defaults: short, decisive, no bounce.

export const ease = {
  outQuart: [0.25, 1, 0.5, 1] as const,
  outExpo: [0.16, 1, 0.3, 1] as const,
  outQuint: [0.22, 1, 0.36, 1] as const,
};

export const duration = {
  fast: 0.12,
  base: 0.18,
  slow: 0.26,
};

// Standard transitions for common motion patterns.
export const transitions = {
  fade: { duration: duration.fast, ease: ease.outQuart },
  swap: { duration: duration.base, ease: ease.outQuart },
  reveal: { duration: duration.slow, ease: ease.outExpo },
};
