import type { ComponentType, ReactNode } from 'react';

// Shared presentational primitives for the System Console panels.

export function severityBadge(severity: string): string {
  switch (severity) {
    case 'pass':
      return 'bg-emerald-500/10 text-emerald-500 border-emerald-500/25';
    case 'warn':
      return 'bg-amber-500/10 text-amber-500 border-amber-500/25';
    default:
      return 'bg-rose-500/10 text-rose-500 border-rose-500/25';
  }
}

export function dotClass(ok: boolean): string {
  return ok ? 'text-emerald-500' : 'text-rose-500';
}

export function SectionCard({
  icon: Icon,
  title,
  hint,
  right,
  children,
}: {
  icon: ComponentType<{ className?: string }>;
  title: string;
  hint?: string;
  right?: ReactNode;
  children: ReactNode;
}) {
  return (
    <section className="glass flex flex-col gap-4 p-5">
      <header className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2.5">
          <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-[var(--accent-soft)] t-accent">
            <Icon className="h-4 w-4" />
          </span>
          <div>
            <h2 className="font-display text-[15px] font-bold tracking-tight t-primary">{title}</h2>
            {hint && <p className="text-[11px] t-faint">{hint}</p>}
          </div>
        </div>
        {right}
      </header>
      {children}
    </section>
  );
}

export function StatTile({
  label,
  value,
  tone = 'neutral',
}: {
  label: string;
  value: ReactNode;
  tone?: 'neutral' | 'good' | 'warn' | 'bad';
}) {
  const toneClass =
    tone === 'good'
      ? 'text-emerald-500'
      : tone === 'warn'
        ? 'text-amber-500'
        : tone === 'bad'
          ? 'text-rose-500'
          : 't-primary';
  return (
    <div className="rounded-lg border brd bg-[var(--surface-inset)] px-3.5 py-3">
      <div className="text-[10px] font-semibold uppercase tracking-wide t-faint">{label}</div>
      <div className={`mt-1 font-mono text-[18px] font-bold tabular-nums ${toneClass}`}>
        {value}
      </div>
    </div>
  );
}

export function KeyValueRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-3 border-b brd py-2 text-[12px] last:border-b-0">
      <span className="t-dim">{label}</span>
      <span className="truncate font-mono font-medium t-primary" title={value}>
        {value}
      </span>
    </div>
  );
}

export function ErrorNote({ message }: { message: string }) {
  return (
    <p className="rounded-lg border border-rose-500/25 bg-rose-500/5 px-3 py-2 text-[12px] text-rose-500">
      {message}
    </p>
  );
}
