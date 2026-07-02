import { motion, AnimatePresence } from 'motion/react';
import { useTranslation } from 'react-i18next';
import {
  Terminal,
  Trash2,
  ShieldAlert,
  CheckCircle2,
  Play,
  RefreshCw,
  Layers,
  Radio,
} from 'lucide-react';
import { useControlStore, type LoggedEvent } from '@/store/useControlStore';
import { TimelinePanel } from '@/components/TimelinePanel';
import { pageVariants } from '@/lib/motion';

function formatTime(ts: number) {
  const d = new Date(ts);
  return d.toTimeString().split(' ')[0] + '.' + String(d.getMilliseconds()).padStart(3, '0');
}

function getEventStyle(type: string) {
  switch (type) {
    case 'plugin.activated':
      return {
        badge: 'bg-emerald-500/10 text-emerald-500 border-emerald-500/25',
        icon: CheckCircle2,
      };
    case 'plugin.failed':
      return {
        badge: 'bg-rose-500/10 text-rose-500 border-rose-500/25',
        icon: ShieldAlert,
      };
    case 'plugin.reloaded':
      return {
        badge: 'bg-[var(--accent-soft)] t-accent border-[var(--accent-border)]',
        icon: RefreshCw,
      };
    case 'baselithcontrol.action':
      return {
        badge: 'bg-sky-500/10 text-sky-500 border-sky-500/25',
        icon: Play,
      };
    default:
      return {
        badge: 'surf t-dim brd',
        icon: Layers,
      };
  }
}

function EventRow({ event }: { event: LoggedEvent }) {
  const { t } = useTranslation();
  const style = getEventStyle(event.type);
  const Icon = style.icon;

  const plugin = typeof event.data?.plugin === 'string' ? event.data.plugin : null;
  const op = typeof event.data?.op === 'string' ? event.data.op : null;
  const ok = event.data?.ok === true;
  const message = typeof event.data?.message === 'string' ? event.data.message : null;

  return (
    <motion.div
      initial={{ opacity: 0, x: -10, y: 5 }}
      animate={{ opacity: 1, x: 0, y: 0 }}
      className="grid gap-2 border-b brd py-3 font-mono text-xs last:border-b-0 lg:grid-cols-[10rem_1fr]"
    >
      <div className="flex flex-wrap items-center gap-2 lg:items-start">
        <span className="select-none tabular-nums t-faint">{formatTime(event.timestamp)}</span>
        <span
          className={`inline-flex items-center gap-1 rounded-md border px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-wide ${style.badge}`}
        >
          <Icon className="h-3 w-3" />
          {event.type.replace('baselithcontrol.', '')}
        </span>
      </div>

      <div className="min-w-0 text-[11px] t-dim">
        {plugin && (
          <div className="mb-1 font-sans text-[12px] font-semibold t-accent">{plugin}</div>
        )}
        {event.type === 'baselithcontrol.action' ? (
          <div>
            {t('events.operation')}: <span className="font-semibold uppercase t-primary">{op}</span>{' '}
            · {t('events.status')}:{' '}
            <span className={ok ? 'font-semibold text-emerald-500' : 'font-semibold text-rose-500'}>
              {ok ? t('events.success') : t('events.failed')}
            </span>{' '}
            {message && `(${message})`}
          </div>
        ) : (
          <pre className="max-w-full overflow-x-auto whitespace-pre-wrap rounded-md border brd surf p-2 leading-relaxed t-dim">
            {JSON.stringify(event.data, null, 2)}
          </pre>
        )}
      </div>
    </motion.div>
  );
}

export function EventFeed() {
  const { t } = useTranslation();
  const events = useControlStore((s) => s.events);
  const clearEvents = useControlStore((s) => s.clearEvents);
  const connected = useControlStore((s) => s.connected);

  return (
    <motion.div
      variants={pageVariants}
      initial="hidden"
      animate="show"
      exit="exit"
      className="space-y-6"
    >
      <div className="flex flex-col gap-3 border-b brd pb-5 sm:flex-row sm:items-end sm:justify-between">
        <div className="space-y-1">
          <h1 className="font-display text-[1.6rem] font-bold leading-tight tracking-tight t-primary">
            {t('events.title')}
          </h1>
          <p className="text-[13px] t-dim">{t('events.subtitle')}</p>
        </div>
        <div className="flex items-center gap-2">
          <span className="inline-flex items-center gap-1.5 rounded-lg border brd bg-[var(--surface-inset)] px-3 py-2 text-[12px] font-medium t-dim">
            <Radio
              className={`h-3.5 w-3.5 ${connected ? 'status-pulse text-emerald-500' : 'text-amber-500'}`}
            />
            {connected ? t('status.live') : t('status.offline')}
          </span>
          {events.length > 0 && (
            <button
              type="button"
              onClick={clearEvents}
              className="inline-flex items-center gap-2 rounded-lg border border-rose-500/25 bg-rose-500/5 px-3.5 py-2 text-[13px] font-medium text-rose-500 transition hover:bg-rose-500/10"
            >
              <Trash2 className="h-3.5 w-3.5" />
              {t('events.clear')}
            </button>
          )}
        </div>
      </div>

      {/* Retained recent-activity timeline (survives reloads) — sits above the
          ephemeral live SSE stream below; both belong to this Events surface. */}
      <TimelinePanel />

      <div className="glass flex min-h-[400px] flex-col overflow-hidden p-5">
        {events.length === 0 ? (
          <div className="flex flex-1 flex-col items-center justify-center space-y-3 py-20 text-center">
            <span className="flex h-12 w-12 items-center justify-center rounded-lg surf t-dim">
              <Terminal className={`h-5 w-5 ${connected ? 'status-pulse' : ''}`} />
            </span>
            <div>
              <p className="text-[14px] font-semibold t-primary">
                {connected ? t('events.console_online') : t('events.console_offline')}
              </p>
              <p className="mt-1 max-w-xs text-[12px] leading-relaxed t-dim">
                {connected ? t('events.empty') : t('events.reconnecting')}
              </p>
            </div>
          </div>
        ) : (
          <div className="max-h-[600px] space-y-1 overflow-y-auto pr-2">
            <AnimatePresence initial={false}>
              {events.map((e) => (
                <EventRow key={e.id} event={e} />
              ))}
            </AnimatePresence>
          </div>
        )}
      </div>
    </motion.div>
  );
}
