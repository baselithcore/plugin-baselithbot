import type { Severity } from '../../lib/api';

export interface HoverInfo {
  x: number;
  y: number;
  label: string;
  display: string;
  severity: Severity | null;
}

export function HoverTooltip({ info }: { info: HoverInfo | null }) {
  if (!info) return null;
  const sevColor: Record<string, string> = {
    info: '#4cc9f0',
    low: '#2dd4bf',
    medium: '#ffb000',
    high: '#ff7a18',
    critical: '#ff3860',
  };
  return (
    <div
      role="tooltip"
      className="pointer-events-none absolute z-40 max-w-[280px] rounded border border-bg-line bg-bg-overlay/95 px-3 py-2 text-xs shadow-glow backdrop-blur"
      style={{ left: info.x + 12, top: info.y + 12 }}
    >
      <p className="font-display text-[10px] uppercase tracking-wider text-text-muted">
        {info.label}
      </p>
      <p className="mt-0.5 break-all font-display text-text-primary">{info.display}</p>
      {info.severity && (
        <p className="mt-1 flex items-center gap-1.5 font-display text-[11px]">
          <span
            className="inline-block h-2 w-2 rounded-full"
            style={{ background: sevColor[info.severity] ?? '#6b7a90' }}
          />
          <span style={{ color: sevColor[info.severity] ?? '#6b7a90' }}>
            {info.severity.toUpperCase()}
          </span>
        </p>
      )}
    </div>
  );
}
