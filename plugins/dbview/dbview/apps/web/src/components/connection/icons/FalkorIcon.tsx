import type { SVGProps } from 'react';

/**
 * FalkorDB brand glyph — connected graph nodes in their signature red,
 * evoking the project's property-graph identity. Not in simple-icons.
 */
export function FalkorIcon({
  size = 24,
  color,
  ...rest
}: SVGProps<SVGSVGElement> & { size?: number; color?: string }) {
  const fill = color ?? '#FF4438';
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
      <line x1="6" y1="6" x2="18" y2="6" stroke={fill} strokeWidth="1.5" />
      <line x1="6" y1="6" x2="6" y2="18" stroke={fill} strokeWidth="1.5" />
      <line x1="6" y1="6" x2="18" y2="18" stroke={fill} strokeWidth="1.5" />
      <line x1="18" y1="6" x2="18" y2="18" stroke={fill} strokeWidth="1.5" />
      <circle cx="6" cy="6" r="2.6" fill={fill} />
      <circle cx="18" cy="6" r="2.6" fill={fill} />
      <circle cx="6" cy="18" r="2.6" fill={fill} />
      <circle cx="18" cy="18" r="2.6" fill={fill} />
    </svg>
  );
}
