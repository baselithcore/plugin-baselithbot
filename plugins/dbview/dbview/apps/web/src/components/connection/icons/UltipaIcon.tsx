import type { SVGProps } from 'react';

/**
 * Ultipa brand glyph — hexagonal/triangular graph motif in their violet.
 * Not in simple-icons; inline approximation.
 */
export function UltipaIcon({
  size = 24,
  color,
  ...rest
}: SVGProps<SVGSVGElement> & { size?: number; color?: string }) {
  const fill = color ?? '#7C3AED';
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
      <path
        d="M12 3 L21 7.5 L21 16.5 L12 21 L3 16.5 L3 7.5 Z"
        stroke={fill}
        strokeWidth="1.5"
        fill="none"
      />
      <circle cx="12" cy="3" r="1.8" fill={fill} />
      <circle cx="21" cy="7.5" r="1.8" fill={fill} />
      <circle cx="21" cy="16.5" r="1.8" fill={fill} />
      <circle cx="12" cy="21" r="1.8" fill={fill} />
      <circle cx="3" cy="16.5" r="1.8" fill={fill} />
      <circle cx="3" cy="7.5" r="1.8" fill={fill} />
      <circle cx="12" cy="12" r="2.5" fill={fill} />
    </svg>
  );
}
