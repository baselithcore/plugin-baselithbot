/**
 * BaselithAuth brand mark — the shield/lock used on the login screen.
 * Single source of truth, reused by the login page and the admin panel so the
 * brand is consistent everywhere.
 */

interface AuthLogoProps {
  size?: number;
  className?: string;
}

export default function AuthLogo({ size = 80, className = '' }: AuthLogoProps) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 64 64"
      fill="none"
      width={size}
      height={size}
      role="img"
      aria-label="BaselithAuth"
      className={className}
    >
      <defs>
        <linearGradient
          id="hydra_grad"
          x1="0"
          y1="0"
          x2="64"
          y2="64"
          gradientUnits="userSpaceOnUse"
        >
          <stop stopColor="#7ee0ff" />
          <stop offset="1" stopColor="#7c8cff" />
        </linearGradient>
      </defs>
      {/* Background shield */}
      <path
        d="M32 4L54 12V30C54 44.4 44.6 57.6 32 62C19.4 57.6 10 44.4 10 30V12L32 4Z"
        fill="#04060f"
        stroke="url(#hydra_grad)"
        strokeWidth="2"
      />
      {/* Central hexagon */}
      <path d="M32 18L44 25V39L32 46L20 39V25L32 18Z" fill="url(#hydra_grad)" opacity="0.9">
        <animate attributeName="opacity" values="0.7;1;0.7" dur="3s" repeatCount="indefinite" />
      </path>
      {/* Inner lock detail */}
      <circle cx="32" cy="30" r="3" fill="#04060f" />
      <rect x="30" y="32" width="4" height="6" rx="1" fill="#04060f" />
    </svg>
  );
}
