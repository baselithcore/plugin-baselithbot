/**
 * Deterministic categorical palette for graph labels / relationship types.
 * Same key → same color across renders. HSL with high chroma, dark-theme tuned.
 */
const HUE_STEP = 47;
const SAT = 70;
const LIGHT = 60;

export function colorForKey(key: string): string {
  let hash = 0;
  for (let i = 0; i < key.length; i++) {
    hash = (hash << 5) - hash + key.charCodeAt(i);
    hash |= 0;
  }
  const hue = Math.abs(hash * HUE_STEP) % 360;
  return `hsl(${hue}, ${SAT}%, ${LIGHT}%)`;
}

export function dimColor(color: string, alpha = 0.18): string {
  const m = color.match(/^hsl\((\d+),\s*(\d+)%,\s*(\d+)%\)$/);
  if (!m) return color;
  return `hsla(${m[1]}, ${m[2]}%, ${m[3]}%, ${alpha})`;
}
