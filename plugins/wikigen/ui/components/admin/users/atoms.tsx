import type { ReactNode } from 'react';
import { cn } from '../../../lib/cn';

export function Th({ children }: { children: ReactNode }) {
  return (
    <th className="border-b border-[var(--color-border)] px-5 py-2 text-left font-semibold tracking-wide">
      {children}
    </th>
  );
}

export function Td({ children, className }: { children: ReactNode; className?: string }) {
  return <td className={'px-5 py-2.5 align-middle ' + (className ?? '')}>{children}</td>;
}

export type ChipTone = 'neutral' | 'success' | 'danger' | 'brand' | 'warn';

const CHIP_TONES: Record<ChipTone, string> = {
  neutral: 'bg-[var(--color-surface)] text-ink-subtle',
  success: 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-400',
  danger: 'bg-rose-500/10 text-rose-700 dark:text-rose-400',
  brand: 'bg-[var(--color-brand-soft)] text-[var(--color-brand-contrast)]',
  warn: 'bg-amber-500/10 text-amber-700 dark:text-amber-400',
};

export function Chip({
  children,
  tone = 'neutral',
  className,
}: {
  children: ReactNode;
  tone?: ChipTone;
  className?: string;
}) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-[10px] font-medium',
        CHIP_TONES[tone],
        className
      )}
    >
      {children}
    </span>
  );
}

const ROLE_TONE: Record<string, ChipTone> = {
  superuser: 'danger',
  admin: 'warn',
  moderator: 'brand',
  user: 'neutral',
};

export function RoleBadge({
  slug,
  className,
  size = 'sm',
}: {
  slug: string;
  className?: string;
  size?: 'sm' | 'md';
}) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 rounded-full px-2 py-0.5 font-medium',
        size === 'md' ? 'text-[11px]' : 'text-[10px]',
        CHIP_TONES[ROLE_TONE[slug] ?? 'neutral'],
        className
      )}
    >
      <span className="size-1.5 rounded-full bg-current opacity-70" aria-hidden />
      {slug}
    </span>
  );
}

function initials(email: string, displayName: string): string {
  const src = (displayName || email).trim();
  if (!src) return '?';
  const parts = src.split(/[\s._-]+/).filter(Boolean);
  if (parts.length >= 2) return (parts[0][0] + parts[1][0]).toUpperCase();
  return src.slice(0, 2).toUpperCase();
}

function hashHue(seed: string): number {
  let h = 0;
  for (let i = 0; i < seed.length; i++) h = (h * 31 + seed.charCodeAt(i)) >>> 0;
  return h % 360;
}

export function Avatar({
  email,
  displayName,
  size = 36,
  className,
}: {
  email: string;
  displayName?: string;
  size?: number;
  className?: string;
}) {
  const hue = hashHue(email);
  return (
    <span
      className={cn(
        'inline-flex shrink-0 items-center justify-center rounded-full font-semibold text-white',
        className
      )}
      style={{
        width: size,
        height: size,
        fontSize: Math.round(size * 0.36),
        background: `linear-gradient(135deg, hsl(${hue} 70% 52%), hsl(${(hue + 35) % 360} 70% 42%))`,
      }}
      aria-hidden
    >
      {initials(email, displayName ?? '')}
    </span>
  );
}
