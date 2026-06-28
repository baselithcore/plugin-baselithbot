import { useMemo, useState } from 'react';
import { motion } from 'motion/react';
import { useTranslation } from 'react-i18next';
import { Search, Pause, Play, FileText } from 'lucide-react';
import { pageVariants } from '@/lib/motion';
import { useLogs } from '@/hooks/useLogs';
import { LogRow } from './Row';

const LEVELS = ['', 'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'] as const;

export function Logs() {
  const { t } = useTranslation();
  const [level, setLevel] = useState('');
  const [plugin, setPlugin] = useState('');
  const [q, setQ] = useState('');
  const [paused, setPaused] = useState(false);

  const query = useMemo(
    () => ({
      limit: 500,
      level: level || undefined,
      plugin: plugin || undefined,
      q: q || undefined,
    }),
    [level, plugin, q]
  );
  const { data, loading, error } = useLogs(query, paused);

  const entries = data?.entries ?? [];
  const plugins = data?.plugins ?? [];

  return (
    <motion.div
      variants={pageVariants}
      initial="hidden"
      animate="show"
      exit="exit"
      className="space-y-4"
    >
      <div className="flex flex-col gap-1 border-b brd pb-4">
        <h1 className="font-display text-[1.6rem] font-bold leading-tight tracking-tight t-primary">
          {t('logs.title')}
        </h1>
        <p className="text-[13px] t-dim">{t('logs.subtitle')}</p>
      </div>

      {/* Filter deck */}
      <div className="glass flex flex-col gap-3 p-3 lg:flex-row lg:items-center">
        <div className="relative w-full lg:max-w-xs">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 t-faint" />
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder={t('logs.search')}
            className="control-field ph-faint w-full rounded-lg py-2 pl-9 pr-3 text-[13px] t-primary outline-none transition focus:border-[var(--accent-border)]"
          />
        </div>

        <select
          value={level}
          onChange={(e) => setLevel(e.target.value)}
          className="control-field cursor-pointer rounded-lg px-3 py-2 text-[13px] font-medium t-primary outline-none"
        >
          {LEVELS.map((lv) => (
            <option key={lv || 'all'} value={lv} className="bg-[var(--surface-1)]">
              {lv ? lv : t('logs.all_levels')}
            </option>
          ))}
        </select>

        <select
          value={plugin}
          onChange={(e) => setPlugin(e.target.value)}
          className="control-field cursor-pointer rounded-lg px-3 py-2 text-[13px] font-medium t-primary outline-none"
        >
          <option value="" className="bg-[var(--surface-1)]">
            {t('logs.all_plugins')}
          </option>
          {plugins.map((p) => (
            <option key={p} value={p} className="bg-[var(--surface-1)]">
              {p}
            </option>
          ))}
        </select>

        <div className="flex items-center gap-2 lg:ml-auto">
          <span className="hidden text-[12px] tabular-nums t-faint sm:block">
            {t('logs.showing', { count: entries.length })}
          </span>
          <button
            type="button"
            onClick={() => setPaused((p) => !p)}
            aria-pressed={paused}
            className={`flex items-center gap-1.5 rounded-lg border px-3 py-2 text-[12px] font-semibold transition ${
              paused
                ? 'border-[var(--accent-border)] bg-[var(--accent-soft)] t-accent'
                : 'brd t-dim hover:bg-[var(--surface-2)]'
            }`}
          >
            {paused ? <Play className="h-3.5 w-3.5" /> : <Pause className="h-3.5 w-3.5" />}
            {paused ? t('logs.resume') : t('logs.pause')}
          </button>
        </div>
      </div>

      {/* Log stream */}
      {error ? (
        <div className="glass border-rose-500/25 p-6 text-sm text-rose-500">
          {error.includes('403') ? t('logs.forbidden') : error}
        </div>
      ) : (
        <div className="glass overflow-hidden">
          {entries.length === 0 ? (
            <div className="flex flex-col items-center gap-2 p-12 text-center">
              <FileText className="h-6 w-6 t-faint" />
              <p className="text-[13px] t-dim">{loading ? t('logs.loading') : t('logs.empty')}</p>
            </div>
          ) : (
            <div className="max-h-[65vh] overflow-y-auto">
              {entries.map((e) => (
                <LogRow key={e.seq} entry={e} />
              ))}
            </div>
          )}
        </div>
      )}
    </motion.div>
  );
}
