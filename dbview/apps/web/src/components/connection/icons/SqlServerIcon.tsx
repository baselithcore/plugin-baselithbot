import type { SVGProps } from 'react';

/**
 * Microsoft SQL Server brand glyph — stacked cylinders in the official red.
 * Simple-icons does not ship the SQL Server logo (Microsoft trademark policy),
 * so we render an inline mark consistent with Microsoft's database iconography.
 */
export function SqlServerIcon({
  size = 24,
  color,
  ...rest
}: SVGProps<SVGSVGElement> & { size?: number; color?: string }) {
  const fill = color ?? '#A91D22';
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
      <ellipse cx="12" cy="5.5" rx="7" ry="2.3" fill={fill} />
      <path
        d="M5 5.5v5c0 1.27 3.13 2.3 7 2.3s7-1.03 7-2.3v-5c0 1.27-3.13 2.3-7 2.3S5 6.77 5 5.5z"
        fill={fill}
        opacity="0.85"
      />
      <path
        d="M5 10.5v5c0 1.27 3.13 2.3 7 2.3s7-1.03 7-2.3v-5c0 1.27-3.13 2.3-7 2.3s-7-1.03-7-2.3z"
        fill={fill}
        opacity="0.7"
      />
      <path
        d="M5 15.5v3c0 1.27 3.13 2.3 7 2.3s7-1.03 7-2.3v-3c0 1.27-3.13 2.3-7 2.3s-7-1.03-7-2.3z"
        fill={fill}
        opacity="0.55"
      />
    </svg>
  );
}
