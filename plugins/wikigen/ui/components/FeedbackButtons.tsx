import { AnimatePresence, motion } from 'framer-motion';
import { ThumbsDown, ThumbsUp, X } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';
import { toast } from 'sonner';
import { submitFeedback } from '../lib/api';
import { DOWN_REASONS, getFeedback, setFeedback, type Feedback } from '../lib/feedback';
import { cn } from '../lib/cn';
import { duration, ease } from '../lib/motion';
import type { Source } from '../lib/types';

interface Props {
  messageId: string;
  answer?: string;
  question?: string;
  sources?: Source[];
  edition?: string | null;
}

export function FeedbackButtons({ messageId, answer, question, sources, edition }: Props) {
  const sendToBackend = (rating: 'up' | 'down', reason?: string) => {
    void submitFeedback({
      message_id: messageId,
      rating,
      reason,
      question,
      answer: answer?.slice(0, 4000),
      sources: sources?.map((s) => ({
        document_id: s.document_id,
        title: s.title,
        score: s.score,
      })),
      edition: edition ?? undefined,
      at: Date.now(),
    });
  };
  const [fb, setFb] = useState<Feedback | null>(() => getFeedback(messageId));
  const [popoverOpen, setPopoverOpen] = useState(false);
  const [selectedReasons, setSelectedReasons] = useState<string[]>([]);
  const [note, setNote] = useState('');
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!popoverOpen) return;
    const onClick = (e: MouseEvent) => {
      if (!ref.current?.contains(e.target as Node)) setPopoverOpen(false);
    };
    window.addEventListener('mousedown', onClick);
    return () => window.removeEventListener('mousedown', onClick);
  }, [popoverOpen]);

  const persist = (next: Feedback | null) => {
    setFb(next);
    setFeedback(messageId, next);
  };

  const handleUp = () => {
    if (fb?.rating === 'up') {
      persist(null);
      return;
    }
    persist({ rating: 'up', at: Date.now() });
    sendToBackend('up');
    toast.success('Grazie per il feedback.');
  };

  const handleDown = () => {
    if (fb?.rating === 'down') {
      persist(null);
      setPopoverOpen(false);
      return;
    }
    persist({ rating: 'down', at: Date.now() });
    setSelectedReasons([]);
    setNote('');
    setPopoverOpen(true);
  };

  const toggleReason = (id: string) => {
    setSelectedReasons((prev) =>
      prev.includes(id) ? prev.filter((r) => r !== id) : [...prev, id]
    );
  };

  const submitReasons = () => {
    const reason = [...selectedReasons, note.trim()].filter(Boolean).join(' · ');
    persist({ rating: 'down', reason: reason || undefined, at: Date.now() });
    sendToBackend('down', reason || undefined);
    setPopoverOpen(false);
    toast.success('Feedback registrato. Grazie.');
  };

  return (
    <div className="relative inline-flex items-center gap-1" ref={ref}>
      <button
        onClick={handleUp}
        aria-pressed={fb?.rating === 'up'}
        className={cn(
          'focus-ring inline-flex items-center gap-1 rounded-md border px-2 py-1 text-[10px] font-medium transition-colors',
          fb?.rating === 'up'
            ? 'bg-[var(--color-success)]/15 border-transparent text-[var(--color-success)]'
            : 'bg-[var(--color-surface)] border-[var(--color-border)] text-ink-muted hover:text-ink'
        )}
        title="Risposta utile"
      >
        <ThumbsUp size={11} />
      </button>
      <button
        onClick={handleDown}
        aria-pressed={fb?.rating === 'down'}
        className={cn(
          'focus-ring inline-flex items-center gap-1 rounded-md border px-2 py-1 text-[10px] font-medium transition-colors',
          fb?.rating === 'down'
            ? 'bg-[var(--color-danger)]/15 border-transparent text-[var(--color-danger)]'
            : 'bg-[var(--color-surface)] border-[var(--color-border)] text-ink-muted hover:text-ink'
        )}
        title="Risposta da migliorare"
      >
        <ThumbsDown size={11} />
      </button>

      <AnimatePresence>
        {popoverOpen && (
          <motion.div
            initial={{ opacity: 0, y: -4, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -4, scale: 0.98 }}
            transition={{ duration: duration.fast, ease: ease.outQuart }}
            className="absolute left-0 top-full mt-2 z-30 w-[300px]
                       rounded-xl border border-[var(--color-border)] bg-[var(--color-canvas-raised)]
                       shadow-lg p-3"
            role="dialog"
            aria-modal="false"
            aria-label="motivo feedback negativo"
          >
            <div className="flex items-center justify-between mb-2">
              <span className="text-[10px] font-semibold uppercase text-ink-subtle">
                Cosa c'è di sbagliato?
              </span>
              <button
                onClick={() => setPopoverOpen(false)}
                className="focus-ring p-0.5 text-ink-subtle hover:text-ink"
                aria-label="chiudi"
              >
                <X size={11} />
              </button>
            </div>
            <div className="flex flex-wrap gap-1 mb-2">
              {DOWN_REASONS.map((r) => (
                <button
                  key={r.id}
                  onClick={() => toggleReason(r.id)}
                  className={cn(
                    'focus-ring rounded-md px-1.5 py-0.5 text-[10px] border transition-colors',
                    selectedReasons.includes(r.id)
                      ? 'bg-[var(--color-brand)] text-white border-transparent'
                      : 'bg-[var(--color-surface)] border-[var(--color-border)] text-ink-muted hover:text-ink'
                  )}
                >
                  {r.label}
                </button>
              ))}
            </div>
            <textarea
              value={note}
              onChange={(e) => setNote(e.target.value)}
              placeholder="Nota opzionale (cosa manca? cita articolo corretto…)"
              rows={2}
              className="focus-ring w-full rounded-md
                         bg-[var(--color-surface)] border border-[var(--color-border)]
                         px-2 py-1.5 text-[11px] placeholder:text-ink-subtle resize-none"
            />
            <div className="mt-2 flex justify-end gap-1.5">
              <button
                onClick={() => {
                  persist(null);
                  setPopoverOpen(false);
                }}
                className="focus-ring inline-flex items-center rounded-md border border-[var(--color-border)]
                           bg-[var(--color-surface)] px-2 py-1 text-[10px] text-ink-muted hover:text-ink"
              >
                Annulla
              </button>
              <button
                onClick={submitReasons}
                className="focus-ring inline-flex items-center rounded-md bg-[var(--color-brand)]
                           px-2.5 py-1 text-[10px] font-medium text-white hover:bg-[var(--color-brand-strong)]"
              >
                Salva
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
