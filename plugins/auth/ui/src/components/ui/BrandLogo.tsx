/**
 * BaselithCore brand mark — a hexagonal "core" monogram with concentric
 * layers and a softly pulsing center. Cyan→indigo gradient matching the
 * dashboard accent. Reused by the login screen and the admin header.
 */

interface BrandLogoProps {
  size?: number;
  animated?: boolean;
  className?: string;
}

export default function BrandLogo({ size = 64, animated = true, className = '' }: BrandLogoProps) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 64 64"
      width={size}
      height={size}
      fill="none"
      role="img"
      aria-label="BaselithCore"
      className={`brand-logo ${animated ? 'is-animated' : ''} ${className}`}
    >
      <defs>
        <linearGradient id="bc-grad" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#00d9ff" />
          <stop offset="1" stopColor="#6366f1" />
        </linearGradient>
        <radialGradient id="bc-core" cx="0.5" cy="0.5" r="0.5">
          <stop offset="0" stopColor="#7ee8ff" />
          <stop offset="1" stopColor="#6366f1" />
        </radialGradient>
      </defs>

      {/* Outer hexagonal shell */}
      <path
        d="M32 4 54.3 17v30L32 60 9.7 47V17L32 4Z"
        stroke="url(#bc-grad)"
        strokeWidth="2.5"
        strokeLinejoin="round"
        fill="rgba(99,102,241,0.06)"
      />

      {/* Inner layered core */}
      <path
        d="M32 17 45 24.5v15L32 47 19 39.5v-15L32 17Z"
        stroke="url(#bc-grad)"
        strokeWidth="1.5"
        strokeLinejoin="round"
        opacity="0.55"
      />

      {/* Rotating accent ring */}
      <circle
        className="brand-ring"
        cx="32"
        cy="32"
        r="13"
        stroke="url(#bc-grad)"
        strokeWidth="1.5"
        strokeDasharray="3 6"
        strokeLinecap="round"
        opacity="0.85"
      />

      {/* Pulsing center node */}
      <circle className="brand-core" cx="32" cy="32" r="5" fill="url(#bc-core)" />

      <style>{`
        .brand-logo .brand-ring { transform-origin: 32px 32px; }
        .brand-logo .brand-core { transform-origin: 32px 32px; }
        .brand-logo.is-animated .brand-ring { animation: brand-spin 14s linear infinite; }
        .brand-logo.is-animated .brand-core { animation: brand-pulse 3.2s ease-in-out infinite; }
        @keyframes brand-spin { to { transform: rotate(360deg); } }
        @keyframes brand-pulse {
          0%, 100% { opacity: 0.75; transform: scale(1); }
          50% { opacity: 1; transform: scale(1.18); }
        }
        @media (prefers-reduced-motion: reduce) {
          .brand-logo.is-animated .brand-ring,
          .brand-logo.is-animated .brand-core { animation: none; }
        }
      `}</style>
    </svg>
  );
}
