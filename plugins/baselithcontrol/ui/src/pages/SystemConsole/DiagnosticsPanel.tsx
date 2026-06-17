import { useCallback, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Stethoscope, ShieldCheck, Info, SlidersHorizontal, RefreshCw } from 'lucide-react';
import { fetchConfigReport, fetchDoctor, fetchInfo, fetchVerify } from '@/lib/api';
import type { ConfigReport, DoctorReport, InfoReport, VerifyReport } from '@/types';
import { ErrorNote, KeyValueRow, SectionCard, StatTile, severityBadge } from './parts';

interface Data {
  doctor: DoctorReport | null;
  verify: VerifyReport | null;
  info: InfoReport | null;
  config: ConfigReport | null;
}

export function DiagnosticsPanel() {
  const { t } = useTranslation();
  const [data, setData] = useState<Data>({ doctor: null, verify: null, info: null, config: null });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [doctor, verify, info, config] = await Promise.all([
        fetchDoctor(),
        fetchVerify(),
        fetchInfo(),
        fetchConfigReport(),
      ]);
      setData({ doctor, verify, info, config });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'failed');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const { doctor, verify, info, config } = data;

  return (
    <div className="space-y-5">
      <div className="flex justify-end">
        <button
          type="button"
          onClick={() => void load()}
          disabled={loading}
          className="inline-flex items-center gap-2 rounded-lg border brd bg-[var(--surface-inset)] px-3.5 py-2 text-[13px] font-medium t-dim transition hover:bg-[var(--surface-2)] disabled:opacity-50"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} />
          {t('console.refresh')}
        </button>
      </div>

      {error && <ErrorNote message={error} />}

      <SectionCard
        icon={Stethoscope}
        title={t('console.doctor')}
        hint={t('console.doctor_hint')}
        right={
          doctor && (
            <div className="flex gap-3 text-[11px] font-semibold">
              <span className="text-emerald-500">{doctor.passed} ✓</span>
              <span className="text-amber-500">{doctor.warnings} ⚠</span>
              <span className="text-rose-500">{doctor.failed} ✕</span>
            </div>
          )
        }
      >
        <div className="space-y-1.5">
          {doctor?.checks.map((c) => (
            <div
              key={c.name}
              className="flex items-center justify-between gap-3 rounded-lg border brd surf px-3 py-2"
            >
              <div className="min-w-0">
                <div className="text-[13px] font-semibold t-primary">{c.name}</div>
                <div className="truncate text-[11px] t-dim" title={c.details || c.message}>
                  {c.message}
                </div>
              </div>
              <span
                className={`shrink-0 rounded-md border px-2 py-0.5 text-[10px] font-bold uppercase ${severityBadge(c.severity)}`}
              >
                {c.severity}
              </span>
            </div>
          ))}
        </div>
      </SectionCard>

      <div className="grid gap-5 lg:grid-cols-2">
        <SectionCard icon={Info} title={t('console.info')} hint={t('console.info_hint')}>
          {info && (
            <div className="space-y-0.5">
              <KeyValueRow label={t('console.fw_version')} value={info.framework_version} />
              <KeyValueRow label="Python" value={info.python} />
              <KeyValueRow label="OS" value={info.os} />
              <KeyValueRow label={t('console.project')} value={info.project_name} />
              <KeyValueRow label={t('console.plugins')} value={String(info.plugin_count)} />
              <KeyValueRow label={t('console.path')} value={info.project_path} />
            </div>
          )}
        </SectionCard>

        <SectionCard
          icon={ShieldCheck}
          title={t('console.verify')}
          hint={t('console.verify_hint')}
          right={
            verify && (
              <div className="flex gap-3 text-[11px] font-semibold">
                <span className="text-emerald-500">{verify.passed} ✓</span>
                <span className="text-amber-500">{verify.warnings} ⚠</span>
                <span className="text-rose-500">{verify.failed} ✕</span>
              </div>
            )
          }
        >
          <div className="grid grid-cols-2 gap-2">
            {verify?.checks.map((c) => (
              <div
                key={`${c.category}-${c.component}`}
                className="flex items-center gap-2 rounded-md border brd surf px-2.5 py-1.5"
              >
                <span
                  className={`h-2 w-2 shrink-0 rounded-full ${
                    c.status === 'pass'
                      ? 'bg-emerald-500'
                      : c.status === 'warn'
                        ? 'bg-amber-500'
                        : 'bg-rose-500'
                  }`}
                />
                <span className="truncate text-[11px] t-dim" title={c.component}>
                  {c.component}
                </span>
              </div>
            ))}
          </div>
        </SectionCard>
      </div>

      <SectionCard
        icon={SlidersHorizontal}
        title={t('console.config')}
        hint={t('console.config_hint')}
        right={
          config && (
            <span
              className={`rounded-md border px-2 py-0.5 text-[10px] font-bold uppercase ${severityBadge(
                config.valid ? 'pass' : 'fail'
              )}`}
            >
              {config.valid ? t('console.valid') : t('console.invalid')}
            </span>
          )
        }
      >
        <div className="grid gap-4 sm:grid-cols-2">
          {config?.sections.map((s) => (
            <div key={s.name} className="rounded-lg border brd surf p-3">
              <div className="mb-2 text-[12px] font-bold t-accent">{s.title}</div>
              {s.available ? (
                <div className="space-y-0.5">
                  {s.items.map((it) => (
                    <KeyValueRow key={it.key} label={it.key} value={it.value} />
                  ))}
                </div>
              ) : (
                <p className="text-[11px] text-rose-500">{s.error}</p>
              )}
            </div>
          ))}
        </div>
        {config && (
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
            {config.validation.map((v) => (
              <StatTile
                key={v.name}
                label={v.name}
                value={v.passed ? 'OK' : '!'}
                tone={v.passed ? (v.severity === 'warn' ? 'warn' : 'good') : 'bad'}
              />
            ))}
          </div>
        )}
      </SectionCard>
    </div>
  );
}
