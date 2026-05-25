import type { SVGProps } from 'react';

/**
 * Qdrant brand glyph — interlocking triangles forming the company's
 * geometric vector-search mark. Not in simple-icons; renders an inline
 * approximation in their signature red.
 */
export function QdrantIcon({
  size = 24,
  color,
  ...rest
}: SVGProps<SVGSVGElement> & { size?: number; color?: string }) {
  const fill = color ?? '#DC2626';
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
      {...rest}
    >
      <path d="M12 3 L21 8 L21 16 L12 21 L3 16 L3 8 Z" fill={fill} opacity="0.18" />
      <path d="M12 3 L21 8 L12 13 Z" fill={fill} />
      <path d="M3 8 L12 13 L3 16 Z" fill={fill} opacity="0.7" />
      <path d="M12 13 L21 16 L12 21 Z" fill={fill} opacity="0.55" />
    </svg>
  );
}
