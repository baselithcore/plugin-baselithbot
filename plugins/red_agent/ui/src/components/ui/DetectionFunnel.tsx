import { Icon } from './Icon';

interface FunnelStage {
  label: string;
  value: number;
  trend?: { value: string; direction: 'up' | 'down' | 'flat'; positive?: boolean };
  tone?: 'neutral' | 'warn' | 'critical';
}

interface FunnelProps {
  stages: FunnelStage[];
}

const TONE_BAND: Record<NonNullable<FunnelStage['tone']>, string> = {
  neutral: 'from-bg-overlay to-bg-line',
  warn: 'from-accent-warn/15 to-accent-warn/40',
  critical: 'from-sev-high/20 to-sev-critical/55',
};

function formatNumber(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1).replace(/\.0$/, '')}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1).replace(/\.0$/, '')}K`;
  return String(n);
}

export function DetectionFunnel({ stages }: FunnelProps) {
  const max = Math.max(...stages.map((s) => s.value), 1);

  return (
    <div className="space-y-3">
      <div className="grid gap-3 md:grid-cols-4">
        {stages.map((s, i) => {
          const pct = Math.max(10, Math.round((s.value / max) * 100));
          const tone = s.tone ?? 'neutral';
          return (
            <div key={s.label} className="relative">
              <div className="flex items-baseline justify-between">
                <span className="font-display text-3xl font-medium tabular-nums text-text-primary">
                  {formatNumber(s.value)}
                </span>
                {s.trend && (
                  <span
                    className={`inline-flex items-center gap-0.5 text-xs font-mono ${
                      s.trend.direction === 'up'
                        ? s.trend.positive === false
                          ? 'text-sev-critical'
                          : 'text-status-success'
                        : s.trend.direction === 'down'
                          ? s.trend.positive === false
                            ? 'text-status-success'
                            : 'text-sev-critical'
                          : 'text-text-muted'
                    }`}
                  >
                    {s.trend.direction === 'up' && <Icon.ArrowUp size={11} />}
                    {s.trend.direction === 'down' && <Icon.ArrowDown size={11} />}
                    {s.trend.value}
                  </span>
                )}
              </div>
              <div className="mt-0.5 text-xs text-text-muted">{s.label}</div>
              <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-bg-overlay/60">
                <div
                  className={`h-full rounded-full bg-gradient-to-r ${TONE_BAND[tone]} transition-all`}
                  style={{ width: `${pct}%` }}
                />
              </div>
              {i < stages.length - 1 && (
                <span
                  aria-hidden
                  className="pointer-events-none absolute -right-1.5 top-3 hidden text-text-subtle md:block"
                >
                  <Icon.ChevronRight size={14} />
                </span>
              )}
            </div>
          );
        })}
      </div>
      <div className="relative h-12 overflow-hidden rounded-md bg-gradient-funnel">
        <svg
          aria-hidden
          className="absolute inset-0 h-full w-full"
          viewBox="0 0 100 12"
          preserveAspectRatio="none"
        >
          <polygon points="0,0 100,3 100,9 0,12" fill="rgba(7,9,18,0.72)" />
        </svg>
        <div className="relative flex h-full items-center justify-between px-4 font-mono text-2xs uppercase tracking-wider text-text-secondary">
          <span>raw signal</span>
          <span>triage</span>
          <span>active threats</span>
          <span className="text-sev-critical">critical</span>
        </div>
      </div>
    </div>
  );
}
