import type { SVGProps } from 'react';

/**
 * Oracle Corporation wordmark — bold "ORACLE" lettermark in brand red.
 * Simple-icons does not ship the Oracle logo (trademark restrictions).
 * Renders a compact "ORACLE" mark via a stylized O glyph that scales cleanly.
 */
export function OracleIcon({
  size = 24,
  color,
  ...rest
}: SVGProps<SVGSVGElement> & { size?: number; color?: string }) {
  const fill = color ?? '#F80000';
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
        d="M8 7h8a5 5 0 0 1 0 10H8a5 5 0 0 1 0-10zm0 2.5a2.5 2.5 0 0 0 0 5h8a2.5 2.5 0 0 0 0-5H8z"
        fill={fill}
      />
    </svg>
  );
}
