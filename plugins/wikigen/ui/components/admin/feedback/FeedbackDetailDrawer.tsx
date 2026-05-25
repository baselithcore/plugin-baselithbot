/**
 * FeedbackDetailDrawer — dettaglio + triage + moderazione di un feedback.
 *
 * Sezioni:
 * - Header: rating + status + timestamp + utente + id + jump-to-conversation
 * - TriagePanel (sub-componente): status, tag chips, resolution note
 * - Motivazione utente / Domanda / Risposta / Sources
 * - Footer: delete moderazione (gated)
 *
 * Gating UI:
 * - Triage panel editable solo se ``can('feedback.triage')``.
 * - Delete visibile solo se ``can('feedback.delete')``.
 */

import {
  Calendar,
  MessageSquare,
  MessageSquareQuote,
  Trash2,
  User,
} from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import { toast } from 'sonner';

import { useAuth } from '../../../contexts/AuthContext';
import * as feedbackApi from '../../../lib/api/feedback_admin';
import type { FeedbackItem, FeedbackStatus } from '../../../lib/api/feedback_admin';
import { Button, ModalShell } from '../../ui';
import { RatingPill } from './atoms';
import { STATUS_LABEL, TriagePanel } from './TriagePanel';

interface Props {
  feedbackId: string | null;
  suggestedTags: string[];
  onClose: () => void;
  onUpdated: (item: FeedbackItem) => void;
  onDeleted: (id: string) => void;
}

const STATUS_TONE: Record<FeedbackStatus, string> = {
  open: 'bg-amber-500/10 text-amber-700 dark:text-amber-400',
  triaged: 'bg-sky-500/10 text-sky-700 dark:text-sky-400',
  resolved: 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-400',
  dismissed: 'bg-zinc-500/10 text-zinc-600 dark:text-zinc-300',
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

export function FeedbackDetailDrawer({
  feedbackId,
  suggestedTags,
  onClose,
  onUpdated,
  onDeleted,
}: Props) {
  const { can } = useAuth();
  const [item, setItem] = useState<FeedbackItem | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [saving, setSaving] = useState(false);

  const [status, setStatus] = useState<FeedbackStatus>('open');
  const [tags, setTags] = useState<string[]>([]);
  const [note, setNote] = useState('');
  const [tagInput, setTagInput] = useState('');

  const canTriage = can('feedback.triage');
  const canDelete = can('feedback.delete');

  useEffect(() => {
    if (!feedbackId) {
      setItem(null);
      return;
    }
    let cancelled = false;
    setLoading(true);
    setError(null);
    feedbackApi
      .getFeedback(feedbackId)
      .then((r) => {
        if (cancelled) return;
        setItem(r);
        setStatus(r.status);
        setTags(r.tags);
        setNote(r.resolution_note ?? '');
      })
      .catch((e) => {
        if (!cancelled) setError(e instanceof Error ? e.message : 'errore');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [feedbackId]);

  const dirty = useMemo(() => {
    if (!item) return false;
    if (status !== item.status) return true;
    if (note !== (item.resolution_note ?? '')) return true;
    if (tags.length !== item.tags.length) return true;
    const sorted = [...tags].sort();
    const origSorted = [...item.tags].sort();
    return sorted.some((t, i) => t !== origSorted[i]);
  }, [item, status, tags, note]);

  const addTag = (raw: string) => {
    const t = raw.trim().toLowerCase();
    if (!t || tags.includes(t)) return;
    setTags([...tags, t]);
    setTagInput('');
  };

  const removeTag = (t: string) => setTags(tags.filter((x) => x !== t));

  const saveTriage = async () => {
    if (!item) return;
    setSaving(true);
    try {
      const updated = await feedbackApi.patchTriage(item.id, {
        status,
        tags,
        resolution_note: note,
      });
      setItem(updated);
      onUpdated(updated);
      toast.success(`Aggiornato → ${STATUS_LABEL[updated.status]}`);
    } catch (e) {
      toast.error(e instanceof Error ? e.message : 'salvataggio fallito');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!item) return;
    if (
      !window.confirm(
        `Eliminare definitivamente questo feedback? L'azione è irreversibile e verrà tracciata in audit.`
      )
    ) {
      return;
    }
    setDeleting(true);
    try {
      await feedbackApi.deleteFeedback(item.id);
      toast.success('Feedback eliminato');
      onDeleted(item.id);
      onClose();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : 'eliminazione fallita');
    } finally {
      setDeleting(false);
    }
  };

  const openConversation = () => {
    if (!item?.conversation_id) return;
    window.open(`/?conversation=${encodeURIComponent(item.conversation_id)}`, '_blank');
  };

  if (!feedbackId) return null;

  return (
    <ModalShell open onClose={onClose} title="Dettaglio feedback" width="2xl">
      <div className="space-y-4 p-1">
        {loading && (
          <div className="py-8 text-center text-sm text-ink-subtle">Caricamento…</div>
        )}

        {error && (
          <div className="rounded border border-rose-500/40 bg-rose-500/10 p-3 text-sm text-rose-700 dark:text-rose-300">
            {error}
          </div>
        )}

        {item && (
          <>
            <header className="flex flex-wrap items-center gap-3">
              <RatingPill rating={item.rating} />
              <span
                className={
                  'inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-[10px] font-medium ' +
                  STATUS_TONE[item.status]
                }
              >
                {STATUS_LABEL[item.status]}
              </span>
              <span className="inline-flex items-center gap-1 text-[11px] text-ink-subtle">
                <Calendar size={11} />
                {fmtDate(item.created_at)}
              </span>
              <span className="inline-flex items-center gap-1 text-[11px] text-ink-subtle">
                <User size={11} />
                {item.user_email ?? item.user_id ?? '—'}
              </span>
              <span className="font-mono text-[10px] text-ink-subtle">
                id: {item.id.slice(0, 8)}…
              </span>
              {item.conversation_id && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={openConversation}
                  title="apri la conversazione di origine in una nuova tab"
                >
                  <MessageSquare size={12} />
                  Apri conversazione
                </Button>
              )}
            </header>

            <TriagePanel
              status={status}
              setStatus={setStatus}
              tags={tags}
              setTags={setTags}
              tagInput={tagInput}
              setTagInput={setTagInput}
              note={note}
              setNote={setNote}
              suggestedTags={suggestedTags}
              addTag={addTag}
              removeTag={removeTag}
              editable={canTriage}
              dirty={dirty}
              saving={saving}
              onSave={saveTriage}
              resolvedByEmail={item.resolved_by_email}
              resolvedAt={item.resolved_at}
            />

            {item.reason && (
              <section className="rounded-md bg-[var(--color-surface)] p-3 ring-1 ring-[var(--color-border)]">
                <h3 className="mb-1 text-[10px] uppercase tracking-wide text-ink-subtle">
                  Motivazione utente
                </h3>
                <p className="whitespace-pre-wrap text-sm">{item.reason}</p>
              </section>
            )}

            <section>
              <h3 className="mb-1 flex items-center gap-1 text-[10px] uppercase tracking-wide text-ink-subtle">
                <MessageSquareQuote size={11} />
                Domanda
              </h3>
              <p className="whitespace-pre-wrap rounded-md bg-[var(--color-surface)] p-3 text-sm ring-1 ring-[var(--color-border)]">
                {item.question || <em className="text-ink-subtle">non registrata</em>}
              </p>
            </section>

            <section>
              <h3 className="mb-1 text-[10px] uppercase tracking-wide text-ink-subtle">
                Risposta
              </h3>
              <div className="max-h-[40vh] overflow-y-auto rounded-md bg-[var(--color-surface)] p-3 ring-1 ring-[var(--color-border)]">
                <p className="whitespace-pre-wrap text-sm">
                  {item.answer || <em className="text-ink-subtle">non registrata</em>}
                </p>
              </div>
            </section>

            {item.sources && item.sources.length > 0 && (
              <section>
                <h3 className="mb-1 text-[10px] uppercase tracking-wide text-ink-subtle">
                  Fonti ({item.sources.length})
                </h3>
                <ul className="space-y-1">
                  {item.sources.map((s, i) => (
                    <li
                      key={`${s.document_id ?? 'src'}-${i}`}
                      className="flex items-center gap-2 rounded bg-[var(--color-surface)] px-2 py-1 text-[11px] ring-1 ring-[var(--color-border)]"
                    >
                      <span className="truncate font-medium">
                        {s.title ?? s.document_id ?? `fonte ${i + 1}`}
                      </span>
                      {typeof s.score === 'number' && (
                        <span className="ml-auto font-mono text-ink-subtle">
                          {s.score.toFixed(3)}
                        </span>
                      )}
                    </li>
                  ))}
                </ul>
              </section>
            )}

            <footer className="flex items-center gap-2 border-t border-[var(--color-border)] pt-3">
              {item.message_id && (
                <span className="font-mono text-[10px] text-ink-subtle">
                  message: {item.message_id.slice(0, 8)}…
                </span>
              )}
              <div className="ml-auto flex items-center gap-2">
                <Button variant="ghost" size="sm" onClick={onClose}>
                  Chiudi
                </Button>
                {canDelete && (
                  <Button
                    variant="danger"
                    size="sm"
                    onClick={handleDelete}
                    disabled={deleting}
                  >
                    <Trash2 size={13} />
                    {deleting ? 'Elimino…' : 'Elimina'}
                  </Button>
                )}
              </div>
            </footer>
          </>
        )}
      </div>
    </ModalShell>
  );
}
