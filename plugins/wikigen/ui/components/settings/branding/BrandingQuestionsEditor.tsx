import { Plus, Trash2 } from 'lucide-react';
import type { TenantSuggestedQuestion } from '../../../lib/api/admin';
import { Button, IconButton } from '../../ui';
import { SubHeader } from './atoms';

interface Props {
  questions: TenantSuggestedQuestion[];
  onChange: (q: TenantSuggestedQuestion[]) => void;
}

export function BrandingQuestionsEditor({ questions, onChange }: Props) {
  const update = (i: number, patch: Partial<TenantSuggestedQuestion>) => {
    onChange(questions.map((q, idx) => (idx === i ? { ...q, ...patch } : q)));
  };
  const remove = (i: number) => onChange(questions.filter((_, idx) => idx !== i));
  const add = () =>
    onChange([
      ...questions,
      { label: '', prompt: '', hint: '', category: 'default', icon: '' },
    ]);

  return (
    <div className="space-y-3 rounded-md border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-3">
      <div className="flex items-center justify-between">
        <SubHeader title="Domande suggerite" />
        <Button
          variant="secondary"
          onClick={add}
          disabled={questions.length >= 8}
          className="!text-[11px]"
        >
          <Plus size={11} /> Aggiungi
        </Button>
      </div>
      {questions.length === 0 ? (
        <p className="text-[11px] text-ink-subtle">
          Nessuna domanda. Aggiungine fino a 8 — saranno mostrate nella homepage.
        </p>
      ) : (
        <div className="space-y-2">
          {questions.map((q, i) => (
            <div
              key={i}
              className="space-y-1.5 rounded-md border border-[var(--color-border)] bg-[var(--color-canvas-raised)] px-2 py-2"
            >
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-semibold uppercase tracking-wide text-ink-subtle">
                  #{i + 1}
                </span>
                <IconButton
                  icon={Trash2}
                  aria-label="rimuovi domanda"
                  size="sm"
                  onClick={() => remove(i)}
                />
              </div>
              <div className="grid grid-cols-2 gap-1.5">
                <input
                  type="text"
                  value={q.label}
                  onChange={(e) => update(i, { label: e.target.value })}
                  placeholder="Etichetta"
                  className="input-text"
                />
                <input
                  type="text"
                  value={q.category ?? ''}
                  onChange={(e) => update(i, { category: e.target.value })}
                  placeholder="Categoria"
                  className="input-text"
                />
              </div>
              <textarea
                value={q.prompt}
                onChange={(e) => update(i, { prompt: e.target.value })}
                placeholder="Prompt inviato al chat"
                rows={2}
                className="input-text"
              />
              <div className="grid grid-cols-2 gap-1.5">
                <input
                  type="text"
                  value={q.hint ?? ''}
                  onChange={(e) => update(i, { hint: e.target.value })}
                  placeholder="Hint (opzionale)"
                  className="input-text"
                />
                <input
                  type="text"
                  value={q.icon ?? ''}
                  onChange={(e) => update(i, { icon: e.target.value })}
                  placeholder="Icona lucide"
                  className="input-text"
                />
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
