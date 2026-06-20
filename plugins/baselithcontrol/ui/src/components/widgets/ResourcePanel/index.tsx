import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Cpu,
  MemoryStick,
  Network,
  Activity,
  Clock,
  Layers,
  Gauge,
  ChevronDown,
} from 'lucide-react';
import type { ResourcesState } from '@/hooks/useResources';
import { formatBytes, formatRate, formatUptime } from '@/lib/format';
import { GaugeCard } from './GaugeCard';
import { RuntimeTable } from './RuntimeTable';

// Live resource observability for the whole framework + per-plugin request load.
// Framework-wide gauges are real OS metrics (psutil); per-plugin rows are HTTP
// telemetry — the only signal that can be honestly attributed to one in-process
// plugin. Collapsed by default so plugin selection stays the focus; a compact
// summary strip is always visible, full gauges + table reveal on expand.
interface Props {
  state: ResourcesState;
  onOpen?: (name: string) => void;
}

export function ResourcePanel({ state, onOpen }: Props) {
  const { t } = useTranslation();
  const { resources, cpuHistory, netHistory, volumeHistory, plugins, error } = state;
  const [open, setOpen] = useState(false);

  if (error && !resources) {
    return (
      <section className="glass border-rose-500/25 p-3 text-[12px] text-rose-500">
        {t('resources.error', { message: error })}
      </section>
    );
  }

  const r = resources;
  const cpuVal = r?.cpu_percent ?? null;
  const hostCpu = r?.host_cpu_percent;
  const memVal = r?.rss_percent ?? null;
  const available = r?.available !== false;

  const summary = [
    { label: t('resources.cpu'), value: cpuVal != null ? `${cpuVal}%` : '—' },
    { label: t('resources.memory'), value: formatBytes(r?.rss_bytes) },
    {
      label: t('resources.network'),
      value: formatRate((r?.net_recv_bps ?? 0) + (r?.net_sent_bps ?? 0)),
    },
    { label: t('resources.process'), value: t('resources.threads_val', { n: r?.threads ?? '—' }) },
  ];

  return (
    <section className="glass overflow-hidden">
      {/* Always-visible compact summary + expand toggle */}
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        className="flex w-full items-center gap-4 px-4 py-2.5 text-left surf-hover"
      >
        <span className="flex items-center gap-2 text-[12px] font-semibold uppercase tracking-wide t-dim">
          <Activity className="h-3.5 w-3.5 t-faint" />
          {t('resources.title')}
        </span>
        {available ? (
          <span className="flex flex-1 flex-wrap items-center gap-x-4 gap-y-1">
            {summary.map((s) => (
              <span key={s.label} className="flex items-baseline gap-1.5 text-[12px]">
                <span className="t-faint">{s.label}</span>
                <span className="font-mono font-semibold tabular-nums t-primary">{s.value}</span>
              </span>
            ))}
          </span>
        ) : (
          <span className="flex-1 text-[11px] font-medium t-faint">
            {t('resources.unavailable')}
          </span>
        )}
        <ChevronDown
          className={`h-4 w-4 shrink-0 t-faint transition-transform ${open ? 'rotate-180' : ''}`}
        />
      </button>

      {open && (
        <div className="space-y-4 border-t brd p-4">
          {available && (
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
              <GaugeCard
                id="cpu"
                icon={Cpu}
                label={t('resources.cpu')}
                value={cpuVal != null ? `${cpuVal}%` : '—'}
                sub={
                  hostCpu != null
                    ? t('resources.cpu_host', { host: hostCpu, cores: r?.cpu_count ?? '?' })
                    : undefined
                }
                spark={cpuHistory}
              />
              <GaugeCard
                id="mem"
                icon={MemoryStick}
                label={t('resources.memory')}
                value={formatBytes(r?.rss_bytes)}
                sub={
                  memVal != null
                    ? t('resources.mem_sub', {
                        pct: memVal,
                        total: formatBytes(r?.mem_total_bytes),
                      })
                    : undefined
                }
                percent={memVal}
              />
              <GaugeCard
                id="net"
                icon={Network}
                label={t('resources.network')}
                value={formatRate((r?.net_recv_bps ?? 0) + (r?.net_sent_bps ?? 0))}
                sub={t('resources.net_sub', {
                  up: formatRate(r?.net_sent_bps),
                  down: formatRate(r?.net_recv_bps),
                })}
                spark={netHistory}
              />
              <GaugeCard
                id="proc"
                icon={Activity}
                label={t('resources.process')}
                value={t('resources.threads_val', { n: r?.threads ?? '—' })}
                sub={t('resources.proc_sub', {
                  fds: r?.open_fds ?? '—',
                  uptime: formatUptime(r?.uptime_seconds),
                })}
              />
              <GaugeCard
                id="req"
                icon={Gauge}
                label={t('resources.throughput')}
                value={t('resources.rps_val', {
                  n: plugins.reduce((acc, p) => acc + p.rps, 0).toFixed(1),
                })}
                sub={t('resources.window_sub')}
                spark={volumeHistory}
              />
            </div>
          )}

          <div className="flex items-center gap-2">
            <Layers className="h-3.5 w-3.5 t-faint" />
            <h3 className="text-[12px] font-semibold t-dim">{t('resources.per_plugin')}</h3>
            <Clock className="ml-auto h-3 w-3 t-faint" />
            <span className="text-[10px] t-faint">{t('resources.live_hint')}</span>
          </div>
          <RuntimeTable rows={plugins} onOpen={onOpen} />
        </div>
      )}
    </section>
  );
}
