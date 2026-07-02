import { useTranslation } from 'react-i18next';
import type { RuntimeRow } from '@/hooks/useResources';

interface Props {
  rows: RuntimeRow[];
  onOpen?: (name: string) => void;
}

function latencyTone(ms: number): string {
  if (ms >= 1000) return 'text-rose-500';
  if (ms >= 300) return 'text-amber-500';
  return 't-primary';
}

// Per-plugin HTTP telemetry table — the honest per-plugin "load" view (in-process
// plugins can't be split by CPU/RAM). Sorted busiest-first by the backend.
export function RuntimeTable({ rows, onOpen }: Props) {
  const { t } = useTranslation();

  if (rows.length === 0) {
    return (
      <div className="glass rounded-xl p-6 text-center">
        <p className="text-[12px] t-dim">{t('resources.no_traffic')}</p>
      </div>
    );
  }

  return (
    <div className="glass overflow-hidden rounded-xl">
      <table className="w-full text-left text-[12px]">
        <thead>
          <tr className="border-b brd t-faint">
            <th className="px-4 py-2.5 font-semibold uppercase tracking-wider">
              {t('resources.col_plugin')}
            </th>
            <th className="px-3 py-2.5 text-right font-semibold uppercase tracking-wider">
              {t('resources.col_requests')}
            </th>
            <th className="px-3 py-2.5 text-right font-semibold uppercase tracking-wider">
              {t('resources.col_rps')}
            </th>
            <th className="px-3 py-2.5 text-right font-semibold uppercase tracking-wider">
              {t('resources.col_inflight')}
            </th>
            <th className="px-3 py-2.5 text-right font-semibold uppercase tracking-wider">
              {t('resources.col_avg')}
            </th>
            <th className="px-3 py-2.5 text-right font-semibold uppercase tracking-wider">
              {t('resources.col_p95')}
            </th>
            <th className="px-4 py-2.5 text-right font-semibold uppercase tracking-wider">
              {t('resources.col_errors')}
            </th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr
              key={r.plugin}
              onClick={onOpen ? () => onOpen(r.plugin) : undefined}
              className={`border-b brd last:border-0 transition ${
                onOpen ? 'cursor-pointer hover:bg-[var(--surface-2)]' : ''
              }`}
            >
              <td className="px-4 py-2.5 font-medium t-primary">
                {onOpen ? (
                  // Real button so keyboard users can open the detail view too
                  // (the row onClick stays as a larger pointer target).
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      onOpen(r.plugin);
                    }}
                    className="cursor-pointer text-left font-medium t-primary hover:underline"
                  >
                    {r.plugin}
                  </button>
                ) : (
                  r.plugin
                )}
              </td>
              <td className="px-3 py-2.5 text-right font-mono tabular-nums t-dim">
                {r.requests.toLocaleString()}
              </td>
              <td className="px-3 py-2.5 text-right font-mono tabular-nums t-dim">{r.rps}</td>
              <td className="px-3 py-2.5 text-right font-mono tabular-nums t-dim">
                {r.in_flight > 0 ? <span className="t-accent">{r.in_flight}</span> : r.in_flight}
              </td>
              <td
                className={`px-3 py-2.5 text-right font-mono tabular-nums ${latencyTone(r.avg_ms)}`}
              >
                {Math.round(r.avg_ms)}ms
              </td>
              <td
                className={`px-3 py-2.5 text-right font-mono tabular-nums ${latencyTone(r.p95_ms)}`}
              >
                {Math.round(r.p95_ms)}ms
              </td>
              <td className="px-4 py-2.5 text-right font-mono tabular-nums">
                <span className={r.errors > 0 ? 'text-rose-500' : 't-faint'}>
                  {r.errors > 0 ? `${(r.error_rate * 100).toFixed(1)}%` : '0'}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
