// Official BaselithCore mark — three stacked italic bars — recreated as a
// crisp, theme-aware SVG (inherits `currentColor`, so it recolors with the
// accent in either theme and scales to any size without raster blur).
export function BrandMark({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 360 376"
      role="img"
      aria-label="BaselithCore"
      fill="currentColor"
      className={className}
    >
      <path d="M61.7,11.2 Q66.0,0.0 78.0,0.0 L329.0,0.0 Q341.0,0.0 337.9,11.6 L322.1,71.4 Q319.0,83.0 307.0,83.0 L46.0,83.0 Q34.0,83.0 38.3,71.8 Z" />
      <path d="M51.9,115.6 Q55.0,104.0 67.0,104.0 L271.0,104.0 Q283.0,104.0 279.9,115.6 L264.1,175.4 Q261.0,187.0 249.0,187.0 L45.0,187.0 Q33.0,187.0 36.1,175.4 Z" />
      <path d="M42.3,219.9 Q44.0,208.0 56.0,208.0 L330.0,208.0 Q342.0,208.0 339.6,219.8 L310.4,363.2 Q308.0,375.0 296.0,375.0 L32.0,375.0 Q20.0,375.0 21.7,363.1 Z" />
    </svg>
  );
}
