import type { ReactNode } from 'react';

type Tone = 'neutral' | 'ember' | 'info' | 'go' | 'caution' | 'danger';

const ACCENT: Record<Tone, string> = {
  neutral: 'from-hair-strong',
  ember: 'from-ember',
  info: 'from-info',
  go: 'from-go',
  caution: 'from-caution',
  danger: 'from-danger',
};

const ICON_TONE: Record<Tone, string> = {
  neutral: 'text-dim',
  ember: 'text-ember',
  info: 'text-info',
  go: 'text-go',
  caution: 'text-caution',
  danger: 'text-danger',
};

interface Props {
  title?: string;
  eyebrow?: string;
  icon?: ReactNode;
  tone?: Tone;
  actions?: ReactNode;
  className?: string;
  bodyClass?: string;
  children: ReactNode;
}

/** Consistent glass panel with a tinted top accent and optional header. */
export function Panel({
  title,
  eyebrow,
  icon,
  tone = 'neutral',
  actions,
  className = '',
  bodyClass = '',
  children,
}: Props) {
  return (
    <section className={`glass relative overflow-hidden rounded-2xl ${className}`}>
      <div
        className={`pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r ${ACCENT[tone]} to-transparent opacity-70`}
      />
      {(title || actions) && (
        <header className="flex items-center justify-between gap-3 px-4 pt-3.5">
          <div className="flex min-w-0 items-center gap-2">
            {icon && <span className={ICON_TONE[tone]}>{icon}</span>}
            <div className="min-w-0">
              {eyebrow && <div className="eyebrow leading-none">{eyebrow}</div>}
              {title && (
                <h3 className="truncate font-display text-sm font-semibold text-ink">{title}</h3>
              )}
            </div>
          </div>
          {actions && <div className="flex shrink-0 items-center gap-1.5">{actions}</div>}
        </header>
      )}
      <div className={`px-4 pb-4 ${title ? 'pt-3' : 'pt-4'} ${bodyClass}`}>{children}</div>
    </section>
  );
}
