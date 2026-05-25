/**
 * FeedbackFiltersBar — filter form per la lista feedback.
 *
 * Filtri (tutti opzionali, combinabili):
 * - rating (all | up | down)
 * - search (Q/A/reason ILIKE)
 * - range temporale (preset 24h / 7gg / 30gg / 90gg / all + custom from/to)
 * - user_id (per drill-in da audit)
 *
 * Emette ``onChange(filters)`` su submit. Niente auto-fire ad ogni keystroke:
 * il rate-limit admin tollera ma la UX migliora con un solo round-trip.
 */

import { Download, RefreshCw, Search, X } from 'lucide-react';
import { useEffect, useState } from 'react';

import type {
  FeedbackFilters,
  FeedbackStatus,
} from '../../../lib/api/feedback_admin';
import { Button } from '../../ui';

const STATUSES: Array<{ value: FeedbackStatus | ''; label: string }> = [
  { value: '', label: 'tutti' },
  { value: 'open', label: 'aperti' },
  { value: 'triaged', label: 'in lavorazione' },
  { value: 'resolved', label: 'risolti' },
  { value: 'dismissed', label: 'archiviati' },
];

type Preset = '24h' | '7d' | '30d' | '90d' | 'all' | 'custom';

const PRESET_HOURS: Record<Exclude<Preset, 'all' | 'custom'>, number> = {
  '24h': 24,
  '7d': 24 * 7,
  '30d': 24 * 30,
  '90d': 24 * 90,
};

interface Props {
  value: FeedbackFilters;
  total: number;
  loading: boolean;
  canDownload: boolean;
  suggestedTags: string[];
  onChange: (next: FeedbackFilters) => void;
  onRefresh: () => void;
  onDownload: () => void;
}

function presetToSince(preset: Preset): string | null {
  if (preset === 'all' || preset === 'custom') return null;
  const hours = PRESET_HOURS[preset];
  const d = new Date(Date.now() - hours * 3600 * 1000);
  return d.toISOString();
}

export function FeedbackFiltersBar({
  value,
  total,
  loading,
  canDownload,
  suggestedTags,
  onChange,
  onRefresh,
  onDownload,
}: Props) {
  const [rating, setRating] = useState<'' | 'up' | 'down'>(value.rating ?? '');
  const [search, setSearch] = useState(value.search ?? '');
  const [preset, setPreset] = useState<Preset>(value.since ? 'custom' : '7d');
  const [since, setSince] = useState(value.since ?? '');
  const [until, setUntil] = useState(value.until ?? '');
  const [userId, setUserId] = useState(value.user_id ?? '');
  const [statusF, setStatusF] = useState<FeedbackStatus | ''>(value.status ?? '');
  const [tagF, setTagF] = useState<string>(value.tag ?? '');

  useEffect(() => {
    if (preset === 'custom' || preset === 'all') return;
    const next = presetToSince(preset);
    setSince(next ?? '');
    setUntil('');
  }, [preset]);

  const apply = (e?: React.FormEvent) => {
    e?.preventDefault();
    onChange({
      rating: rating || null,
      search: search.trim() || null,
      since: preset === 'all' ? null : since || null,
      until: until || null,
      user_id: userId.trim() || null,
      status: statusF || null,
      tag: tagF.trim() || null,
      offset: 0,
    });
  };

  const reset = () => {
    setRating('');
    setSearch('');
    setPreset('7d');
    setSince(presetToSince('7d') ?? '');
    setUntil('');
    setUserId('');
    setStatusF('');
    setTagF('');
    onChange({
      rating: null,
      search: null,
      since: presetToSince('7d'),
      until: null,
      user_id: null,
      status: null,
      tag: null,
      offset: 0,
    });
  };

  return (
    <form
      onSubmit={apply}
      className="flex flex-wrap items-end gap-3 border-b border-[var(--color-border)] px-5 py-3"
    >
      <div className="flex flex-col gap-1">
        <label className="text-[10px] uppercase tracking-wide text-ink-subtle">
          Periodo
        </label>
        <div className="flex items-center gap-1 rounded-md bg-[var(--color-surface)] p-0.5">
          {(['24h', '7d', '30d', '90d', 'all'] as Preset[]).map((p) => (
            <button
              key={p}
              type="button"
              onClick={() => setPreset(p)}
              className={
                'rounded px-2 py-1 text-[11px] font-medium transition-colors ' +
                (preset === p
                  ? 'bg-[var(--color-brand-soft)] text-[var(--color-brand-contrast)]'
                  : 'text-ink-subtle hover:text-ink')
              }
            >
              {p === 'all' ? 'tutto' : p}
            </button>
          ))}
        </div>
      </div>

      {preset === 'custom' && (
        <div className="flex items-end gap-2">
          <div className="flex flex-col gap-1">
            <label
              className="text-[10px] uppercase tracking-wide text-ink-subtle"
              htmlFor="fb-since"
            >
              Da
            </label>
            <input
              id="fb-since"
              type="datetime-local"
              value={since.slice(0, 16)}
              onChange={(e) =>
                setSince(e.target.value ? new Date(e.target.value).toISOString() : '')
              }
              className="input-sm"
            />
          </div>
          <div className="flex flex-col gap-1">
            <label
              className="text-[10px] uppercase tracking-wide text-ink-subtle"
              htmlFor="fb-until"
            >
              A
            </label>
            <input
              id="fb-until"
              type="datetime-local"
              value={until.slice(0, 16)}
              onChange={(e) =>
                setUntil(e.target.value ? new Date(e.target.value).toISOString() : '')
              }
              className="input-sm"
            />
          </div>
        </div>
      )}

      <div className="flex flex-col gap-1">
        <label className="text-[10px] uppercase tracking-wide text-ink-subtle">
          Rating
        </label>
        <div className="flex items-center gap-1 rounded-md bg-[var(--color-surface)] p-0.5">
          {(['', 'up', 'down'] as const).map((r) => (
            <button
              key={r || 'all'}
              type="button"
              onClick={() => setRating(r)}
              className={
                'rounded px-2 py-1 text-[11px] font-medium transition-colors ' +
                (rating === r
                  ? 'bg-[var(--color-brand-soft)] text-[var(--color-brand-contrast)]'
                  : 'text-ink-subtle hover:text-ink')
              }
            >
              {r === '' ? 'tutti' : r === 'up' ? '👍 up' : '👎 down'}
            </button>
          ))}
        </div>
      </div>

      <div className="flex min-w-[220px] flex-1 flex-col gap-1">
        <label
          className="text-[10px] uppercase tracking-wide text-ink-subtle"
          htmlFor="fb-search"
        >
          Cerca in domanda / risposta / motivazione
        </label>
        <div className="relative">
          <Search
            size={13}
            className="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 text-ink-subtle"
            aria-hidden
          />
          <input
            id="fb-search"
            type="search"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="es. 'errore', 'non corretto', …"
            className="input-sm w-full pl-7"
          />
        </div>
      </div>

      <div className="flex flex-col gap-1">
        <label
          className="text-[10px] uppercase tracking-wide text-ink-subtle"
          htmlFor="fb-status"
        >
          Stato
        </label>
        <select
          id="fb-status"
          value={statusF}
          onChange={(e) => setStatusF(e.target.value as FeedbackStatus | '')}
          className="input-sm"
        >
          {STATUSES.map((s) => (
            <option key={s.value || 'all'} value={s.value}>
              {s.label}
            </option>
          ))}
        </select>
      </div>

      <div className="flex flex-col gap-1">
        <label
          className="text-[10px] uppercase tracking-wide text-ink-subtle"
          htmlFor="fb-tag"
        >
          Tag
        </label>
        <input
          id="fb-tag"
          type="text"
          list="fb-tag-suggest"
          value={tagF}
          onChange={(e) => setTagF(e.target.value)}
          placeholder="es. hallucination"
          className="input-sm w-[180px]"
        />
        <datalist id="fb-tag-suggest">
          {suggestedTags.map((t) => (
            <option key={t} value={t} />
          ))}
        </datalist>
      </div>

      <div className="flex flex-col gap-1">
        <label
          className="text-[10px] uppercase tracking-wide text-ink-subtle"
          htmlFor="fb-userid"
        >
          User ID (opzionale)
        </label>
        <input
          id="fb-userid"
          type="text"
          value={userId}
          onChange={(e) => setUserId(e.target.value)}
          placeholder="uuid"
          className="input-sm w-[200px] font-mono text-[11px]"
        />
      </div>

      <div className="ml-auto flex items-center gap-2">
        <span className="text-[11px] text-ink-subtle">{total} risultati</span>
        <Button type="submit" variant="primary" size="sm" disabled={loading}>
          Applica
        </Button>
        <Button
          type="button"
          variant="ghost"
          size="sm"
          onClick={reset}
          title="reset filtri"
        >
          <X size={13} />
        </Button>
        <Button
          type="button"
          variant="ghost"
          size="sm"
          onClick={onRefresh}
          disabled={loading}
          title="ricarica"
        >
          <RefreshCw size={13} className={loading ? 'animate-spin' : ''} />
        </Button>
        {canDownload && (
          <Button
            type="button"
            variant="secondary"
            size="sm"
            onClick={onDownload}
            disabled={total === 0}
            title="esporta CSV con i filtri correnti"
          >
            <Download size={13} />
            CSV
          </Button>
        )}
      </div>
    </form>
  );
}
