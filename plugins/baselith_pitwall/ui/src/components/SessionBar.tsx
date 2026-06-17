import { useCallback, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Plus, Play, Pause, Square, X } from 'lucide-react';
import { api, getActiveSession, setActiveSession } from '../api';
import type { RaceSession, SourceKind } from '../types';
import { Select } from './ui';

const SOURCES: SourceKind[] = ['simulated', 'file_replay', 'websocket', 'udp', 'manual'];

const STATUS_DOT: Record<string, string> = {
  live: 'bg-go pulse-dot',
  paused: 'bg-caution',
  configuring: 'bg-info',
  finished: 'bg-faint',
  archived: 'bg-faint',
};

interface Props {
  onSessionChange: (id: string) => void;
}

// Session picker + lifecycle controls driving the X-Session-ID sent everywhere.
export function SessionBar({ onSessionChange }: Props) {
  const { t } = useTranslation();
  const [sessions, setSessions] = useState<RaceSession[]>([]);
  const [active, setActive] = useState(getActiveSession());
  const [creating, setCreating] = useState(false);
  const [name, setName] = useState('');
  const [source, setSource] = useState<SourceKind>('simulated');

  const refresh = useCallback(async () => {
    try {
      setSessions(await api.listSessions());
    } catch {
      /* backend warming up */
    }
  }, []);

  useEffect(() => {
    void refresh();
    const id = setInterval(refresh, 4000);
    return () => clearInterval(id);
  }, [refresh]);

  const select = useCallback(
    (id: string) => {
      setActive(id);
      setActiveSession(id);
      onSessionChange(id);
    },
    [onSessionChange]
  );

  const create = useCallback(async () => {
    if (!name.trim()) return;
    const s = await api.createSession({ name: name.trim(), source_kind: source });
    setName('');
    setCreating(false);
    await refresh();
    select(s.id);
    await api.startSession(s.id).catch(() => undefined);
    await refresh();
  }, [name, source, refresh, select]);

  const current = sessions.find((s) => s.id === active);

  const lifecycle = async (verb: 'start' | 'pause' | 'end') => {
    const fn =
      verb === 'start' ? api.startSession : verb === 'pause' ? api.pauseSession : api.endSession;
    await fn(active).catch(() => undefined);
    await refresh();
  };

  const ctrl =
    'grid h-9 w-9 place-items-center rounded-lg border border-hair bg-surface-2 transition hover:border-hair-strong';

  return (
    <div className="flex flex-wrap items-center gap-2">
      <div className="flex items-center gap-2 rounded-lg border border-hair bg-surface-2 pl-2.5">
        <span className={`h-2 w-2 rounded-full ${STATUS_DOT[current?.status ?? 'configuring']}`} />
        <Select value={active} onChange={select} ariaLabel={t('session')} className="min-w-[9rem]">
          {sessions.map((s) => (
            <option key={s.id} value={s.id}>
              {s.name} · {t(`st_${s.status}`)}
            </option>
          ))}
        </Select>
      </div>

      {current && (
        <div className="flex items-center gap-1">
          <button
            onClick={() => lifecycle('start')}
            title={t('start')}
            className={`${ctrl} text-go hover:text-go`}
          >
            <Play size={14} />
          </button>
          <button
            onClick={() => lifecycle('pause')}
            title={t('pause')}
            className={`${ctrl} text-caution`}
          >
            <Pause size={14} />
          </button>
          <button
            onClick={() => lifecycle('end')}
            title={t('end')}
            className={`${ctrl} text-danger`}
          >
            <Square size={14} />
          </button>
        </div>
      )}

      {creating ? (
        <div className="flex flex-wrap items-center gap-2">
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder={t('sessionName')}
            className="rounded-lg border border-hair bg-surface-2 px-3 py-1.5 text-sm text-ink outline-none focus:border-info/60"
          />
          <Select
            value={source}
            onChange={(v) => setSource(v as SourceKind)}
            ariaLabel={t('source')}
          >
            {SOURCES.map((s) => (
              <option key={s} value={s}>
                {t(`src_${s}`)}
              </option>
            ))}
          </Select>
          <button
            onClick={() => void create()}
            className="rounded-lg border border-ember/40 bg-ember/10 px-3 py-1.5 text-sm font-medium text-ember transition hover:bg-ember/20"
          >
            {t('create')}
          </button>
          <button onClick={() => setCreating(false)} title={t('cancel')} className={ctrl}>
            <X size={14} className="text-faint" />
          </button>
        </div>
      ) : (
        <button
          onClick={() => setCreating(true)}
          title={t('newSession')}
          className={`${ctrl} text-dim hover:text-ember`}
        >
          <Plus size={16} />
        </button>
      )}
    </div>
  );
}
