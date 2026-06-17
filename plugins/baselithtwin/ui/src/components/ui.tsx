// Small presentational primitives shared across panels. Centralising Card /
// Badge / Button keeps the visual language consistent and the panels focused on
// composition rather than styling.

import type { ButtonHTMLAttributes, ReactNode } from 'react';

export function Card({
  title,
  action,
  children,
  className = '',
}: {
  title?: ReactNode;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section
      className={`rounded-2xl border border-white/5 bg-ink-800/70 backdrop-blur-xl shadow-2xl shadow-black/30 ${className}`}
    >
      {(title || action) && (
        <header className="flex items-center justify-between px-5 py-4 border-b border-white/5">
          <h2 className="text-sm font-semibold tracking-wide text-white/80">{title}</h2>
          {action}
        </header>
      )}
      <div className="p-5">{children}</div>
    </section>
  );
}

type Tone = 'neutral' | 'good' | 'warn' | 'bad' | 'brand';

const TONES: Record<Tone, string> = {
  neutral: 'bg-white/5 text-white/60 border-white/10',
  good: 'bg-emerald-500/10 text-emerald-300 border-emerald-500/20',
  warn: 'bg-amber-500/10 text-amber-300 border-amber-500/20',
  bad: 'bg-rose-500/10 text-rose-300 border-rose-500/20',
  brand: 'bg-brand-500/10 text-brand-400 border-brand-500/25',
};

export function Badge({ children, tone = 'neutral' }: { children: ReactNode; tone?: Tone }) {
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-xs font-medium ${TONES[tone]}`}
    >
      {children}
    </span>
  );
}

export function Button({
  variant = 'ghost',
  className = '',
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: 'primary' | 'ghost' | 'danger';
}) {
  const styles = {
    primary:
      'bg-brand-500 hover:bg-brand-400 text-ink-900 font-semibold shadow-lg shadow-brand-500/20',
    ghost: 'bg-white/5 hover:bg-white/10 text-white/80 border border-white/10',
    danger: 'bg-rose-500/15 hover:bg-rose-500/25 text-rose-300 border border-rose-500/25',
  }[variant];
  return (
    <button
      className={`rounded-lg px-3.5 py-1.5 text-sm transition-colors disabled:opacity-40 disabled:cursor-not-allowed ${styles} ${className}`}
      {...props}
    />
  );
}
