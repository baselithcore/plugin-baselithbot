/**
 * TriagePanel — sub-componente del drawer feedback per il workflow di
 * triage moderazione (status / tag chips / resolution note).
 *
 * Read-only quando l'utente non ha ``feedback.triage`` — pattern
 * "ghost form" che lascia visibili i field ma disabilitati, così il
 * moderator-in-training capisce cosa fanno gli admin senza dover
 * leggere docs separati.
 */

import { CheckCircle2, Loader2, Plus, X } from 'lucide-react';

import type { FeedbackStatus } from '../../../lib/api/feedback_admin';
import { Button } from '../../ui';

const STATUS_LABEL: Record<FeedbackStatus, string> = {
  open: 'Aperto',
  triaged: 'In lavorazione',
  resolved: 'Risolto',
  dismissed: 'Archiviato',
};

function fmtDate(iso: string | null): string {
  if (!iso) return '—';
  try {
    return new Date(iso).toLocaleString('it-IT', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return iso;
  }
}

export interface TriagePanelProps {
  status: FeedbackStatus;
  setStatus: (s: FeedbackStatus) => void;
  tags: string[];
  setTags: (t: string[]) => void;
  tagInput: string;
  setTagInput: (s: string) => void;
  note: string;
  setNote: (s: string) => void;
  suggestedTags: string[];
  addTag: (raw: string) => void;
  removeTag: (t: string) => void;
  editable: boolean;
  dirty: boolean;
  saving: boolean;
  onSave: () => void;
  resolvedByEmail: string | null;
  resolvedAt: string | null;
}

export function TriagePanel(props: TriagePanelProps) {
  const {
    status,
    setStatus,
    tags,
    tagInput,
    setTagInput,
    note,
    setNote,
    suggestedTags,
    addTag,
    removeTag,
    editable,
    dirty,
    saving,
    onSave,
    resolvedByEmail,
    resolvedAt,
  } = props;
  const availableSuggested = suggestedTags.filter((t) => !tags.includes(t));
  return (
    <section className="rounded-md bg-[var(--color-surface)] p-3 ring-1 ring-[var(--color-border)]">
      <div className="mb-2 flex items-center justify-between">
        <h3 className="text-[10px] uppercase tracking-wide text-ink-subtle">Triage</h3>
        {resolvedAt && (
          <span className="inline-flex items-center gap-1 text-[10px] text-ink-subtle">
            <CheckCircle2 size={11} />
            risolto da {resolvedByEmail ?? '—'} il {fmtDate(resolvedAt)}
          </span>
        )}
      </div>

      <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
        <div>
          <label className="text-[10px] uppercase tracking-wide text-ink-subtle">
            Stato
          </label>
          <select
            value={status}
            onChange={(e) => setStatus(e.target.value as FeedbackStatus)}
            disabled={!editable}
            className="input-sm mt-1 w-full"
          >
            {(['open', 'triaged', 'resolved', 'dismissed'] as FeedbackStatus[]).map(
              (s) => (
                <option key={s} value={s}>
                  {STATUS_LABEL[s]}
                </option>
              )
            )}
          </select>
        </div>

        <div>
          <label className="text-[10px] uppercase tracking-wide text-ink-subtle">
            Tag
          </label>
          <div className="mt-1 flex flex-wrap items-center gap-1 rounded border border-[var(--color-border)] bg-[var(--color-canvas)] p-1.5">
            {tags.map((t) => (
              <span
                key={t}
                className="inline-flex items-center gap-1 rounded bg-[var(--color-brand-soft)] px-1.5 py-0.5 text-[10px] font-medium text-[var(--color-brand-contrast)]"
              >
                {t}
                {editable && (
                  <button
                    type="button"
                    onClick={() => removeTag(t)}
                    aria-label={`rimuovi tag ${t}`}
                    className="hover:text-rose-500"
                  >
                    <X size={10} />
                  </button>
                )}
              </span>
            ))}
            {editable && (
              <input
                type="text"
                value={tagInput}
                onChange={(e) => setTagInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ',') {
                    e.preventDefault();
                    addTag(tagInput);
                  } else if (e.key === 'Backspace' && !tagInput && tags.length > 0) {
                    removeTag(tags[tags.length - 1]);
                  }
                }}
                placeholder={tags.length ? '' : 'aggiungi tag, premi invio'}
                className="min-w-[100px] flex-1 bg-transparent text-[11px] outline-none"
              />
            )}
          </div>
          {editable && availableSuggested.length > 0 && (
            <div className="mt-1 flex flex-wrap gap-1">
              {availableSuggested.map((t) => (
                <button
                  key={t}
                  type="button"
                  onClick={() => addTag(t)}
                  className="inline-flex items-center gap-0.5 rounded border border-dashed border-[var(--color-border)] px-1.5 py-0.5 text-[10px] text-ink-subtle hover:bg-[var(--color-surface-hover)]"
                >
                  <Plus size={9} />
                  {t}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      <div className="mt-3">
        <label className="text-[10px] uppercase tracking-wide text-ink-subtle">
          Note risoluzione
        </label>
        <textarea
          value={note}
          onChange={(e) => setNote(e.target.value)}
          disabled={!editable}
          rows={2}
          maxLength={2000}
          placeholder="es. 'Aggiornato doc X, ri-ingestato il 24/05'"
          className="input-sm mt-1 w-full resize-y"
        />
      </div>

      {editable && (
        <div className="mt-2 flex items-center justify-end gap-2">
          <Button
            variant="primary"
            size="sm"
            onClick={onSave}
            disabled={!dirty || saving}
          >
            {saving && <Loader2 size={12} className="animate-spin" />}
            Salva triage
          </Button>
        </div>
      )}
      {!editable && (
        <p className="mt-2 text-[10px] text-ink-subtle">
          Sola lettura — richiede permesso ``feedback.triage``.
        </p>
      )}
    </section>
  );
}

export { STATUS_LABEL };
