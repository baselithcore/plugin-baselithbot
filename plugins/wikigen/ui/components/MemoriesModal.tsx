/**
 * MemoriesModal (Fase 6.1).
 *
 * CRUD memorie utente: lista + create + delete + search live.
 * Backend embedda sincrono on-write (BGE-M3); UI invia solo testo.
 *
 * Tassonomia kind:
 * - note: testo libero
 * - fact: affermazione dichiarativa
 * - preference: key/value (chiave normalizzata)
 *
 * Search: invio query → backend pgvector cosine top-K. Risultati
 * mostrano similarity score per debug; sotto soglia il backend già
 * filtra (min_similarity=0.0 qui per esposizione completa).
 */

import { type FormEvent, useCallback, useEffect, useState } from 'react';
import { Brain, Plus, Search, Trash2 } from 'lucide-react';

import { Button } from './ui/Button';
import { ModalShell } from './ui/ModalShell';
import {
  type ApiMemory,
  type MemoryKind,
  createMemory,
  deleteMemory,
  listMemories,
  searchMemories,
} from '../lib/api/memories';

interface MemoriesModalProps {
  open: boolean;
  onClose: () => void;
}

const KIND_LABELS: Record<MemoryKind, string> = {
  note: 'Nota',
  fact: 'Fatto',
  preference: 'Preferenza',
};

const KIND_COLORS: Record<MemoryKind, string> = {
  note: 'bg-[var(--color-surface)] text-ink-muted',
  fact: 'bg-[var(--color-brand)]/15 text-[var(--color-brand)]',
  preference: 'bg-[var(--color-accent)]/15 text-[var(--color-accent)]',
};

export function MemoriesModal({ open, onClose }: MemoriesModalProps) {
  const [items, setItems] = useState<ApiMemory[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Create form state
  const [newValue, setNewValue] = useState('');
  const [newKind, setNewKind] = useState<MemoryKind>('note');
  const [newKey, setNewKey] = useState('');
  const [creating, setCreating] = useState(false);

  // Search state
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<ApiMemory[] | null>(null);
  const [searching, setSearching] = useState(false);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const list = await listMemories();
      setItems(list);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'errore caricamento');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (open) void refresh();
  }, [open, refresh]);

  const handleCreate = async (e: FormEvent) => {
    e.preventDefault();
    if (!newValue.trim()) return;
    if (newKind === 'preference' && !newKey.trim()) {
      setError('Le preferenze richiedono una chiave (es: "language", "tone").');
      return;
    }
    setCreating(true);
    setError(null);
    try {
      await createMemory({
        value: newValue.trim(),
        kind: newKind,
        key: newKind === 'preference' ? newKey.trim() : undefined,
      });
      setNewValue('');
      setNewKey('');
      setNewKind('note');
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'creazione fallita');
    } finally {
      setCreating(false);
    }
  };

  const handleDelete = async (id: string) => {
    const snapshot = items;
    setItems((prev) => prev.filter((m) => m.id !== id));
    try {
      await deleteMemory(id);
    } catch (err) {
      setItems(snapshot);
      setError(err instanceof Error ? err.message : 'cancellazione fallita');
    }
  };

  const handleSearch = async (e: FormEvent) => {
    e.preventDefault();
    if (!query.trim()) {
      setResults(null);
      return;
    }
    setSearching(true);
    setError(null);
    try {
      const r = await searchMemories({ query: query.trim(), top_k: 10 });
      setResults(r);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'ricerca fallita');
    } finally {
      setSearching(false);
    }
  };

  const visible = results ?? items;

  return (
    <ModalShell
      open={open}
      onClose={onClose}
      title="Memorie personali"
      icon={Brain}
      subtitle="Fatti e preferenze che il chatbot ricorderà"
      width="xl"
      panelClassName="flex max-h-[85vh] flex-col"
    >
      <div className="flex flex-1 flex-col gap-4 overflow-hidden">
        {/* Create form */}
        <form
          onSubmit={handleCreate}
          className="rounded-lg border border-[var(--color-border)] bg-[var(--color-canvas)] p-3"
        >
          <div className="mb-2 flex items-center justify-between text-[11px] font-medium uppercase tracking-wider text-ink-muted">
            <span>Aggiungi memoria</span>
            <KindToggle value={newKind} onChange={setNewKind} />
          </div>
          {newKind === 'preference' && (
            <input
              type="text"
              value={newKey}
              onChange={(e) => setNewKey(e.target.value)}
              placeholder="chiave (es: language, tone)"
              aria-label="chiave preferenza"
              className="mb-2 w-full rounded border border-[var(--color-border)] bg-[var(--color-canvas-raised)] px-2 py-1.5 text-xs text-ink outline-none transition-colors focus-visible:ring-2 focus-visible:ring-[var(--color-brand-ring)] focus:border-[var(--color-brand)]"
            />
          )}
          <textarea
            value={newValue}
            onChange={(e) => setNewValue(e.target.value)}
            placeholder={
              newKind === 'preference'
                ? 'Valore della preferenza (es: italiano, formale)'
                : newKind === 'fact'
                  ? 'Affermazione dichiarativa (es: lavoro come ingegnere DevOps)'
                  : 'Nota libera (es: ricorda di rispondere conciso)'
            }
            rows={2}
            aria-label="contenuto memoria"
            className="w-full resize-none rounded border border-[var(--color-border)] bg-[var(--color-canvas-raised)] px-2 py-1.5 text-xs text-ink outline-none transition-colors focus-visible:ring-2 focus-visible:ring-[var(--color-brand-ring)] focus:border-[var(--color-brand)]"
          />
          <div className="mt-2 flex justify-end">
            <Button
              type="submit"
              variant="primary"
              size="sm"
              loading={creating}
              disabled={!newValue.trim()}
              leadingIcon={Plus}
            >
              Salva
            </Button>
          </div>
        </form>

        {/* Search */}
        <form onSubmit={handleSearch} className="flex gap-2">
          <div className="relative flex-1">
            <Search
              size={14}
              className="pointer-events-none absolute left-2 top-1/2 -translate-y-1/2 text-ink-muted"
            />
            <input
              type="search"
              value={query}
              onChange={(e) => {
                setQuery(e.target.value);
                if (!e.target.value) setResults(null);
              }}
              placeholder="cerca per similarità (top-10)"
              aria-label="cerca memorie per similarità"
              className="w-full rounded border border-[var(--color-border)] bg-[var(--color-canvas)] py-1.5 pl-7 pr-2 text-xs text-ink outline-none transition-colors focus-visible:ring-2 focus-visible:ring-[var(--color-brand-ring)] focus:border-[var(--color-brand)]"
            />
          </div>
          <Button
            type="submit"
            variant="secondary"
            size="sm"
            loading={searching}
            disabled={!query.trim()}
          >
            Cerca
          </Button>
          {results && (
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={() => {
                setResults(null);
                setQuery('');
              }}
            >
              Reset
            </Button>
          )}
        </form>

        {error && (
          <div className="rounded border border-[var(--color-danger)]/40 bg-[var(--color-danger)]/10 px-3 py-1.5 text-xs text-[var(--color-danger)]">
            {error}
          </div>
        )}

        {/* List */}
        <div className="flex-1 overflow-y-auto pr-1">
          {loading && <div className="text-xs text-ink-muted">Caricamento…</div>}
          {!loading && visible.length === 0 && (
            <div className="rounded border border-dashed border-[var(--color-border)] py-8 text-center text-xs text-ink-muted">
              {results ? 'Nessun risultato.' : 'Nessuna memoria salvata.'}
            </div>
          )}
          <ul className="space-y-2">
            {visible.map((m) => (
              <li
                key={m.id}
                className="group rounded-lg border border-[var(--color-border)] bg-[var(--color-canvas-raised)] p-3"
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="flex-1">
                    <div className="mb-1 flex items-center gap-2 text-[10px] uppercase tracking-wider">
                      <span className={`rounded px-1.5 py-0.5 ${KIND_COLORS[m.kind]}`}>
                        {KIND_LABELS[m.kind]}
                      </span>
                      {m.key && (
                        <span className="rounded bg-[var(--color-surface)] px-1.5 py-0.5 text-ink-muted">
                          {m.key}
                        </span>
                      )}
                      {typeof m.similarity === 'number' && (
                        <span className="text-ink-muted">sim {m.similarity.toFixed(2)}</span>
                      )}
                    </div>
                    <div className="text-sm text-ink">{m.value}</div>
                  </div>
                  <button
                    type="button"
                    onClick={() => void handleDelete(m.id)}
                    className="rounded p-1 text-ink-muted opacity-0 transition-opacity hover:bg-[var(--color-danger)]/10 hover:text-[var(--color-danger)] group-hover:opacity-100"
                    aria-label="Elimina memoria"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </ModalShell>
  );
}

interface KindToggleProps {
  value: MemoryKind;
  onChange: (k: MemoryKind) => void;
}

function KindToggle({ value, onChange }: KindToggleProps) {
  const opts: MemoryKind[] = ['note', 'fact', 'preference'];
  return (
    <div className="flex rounded border border-[var(--color-border)] p-0.5">
      {opts.map((k) => (
        <button
          key={k}
          type="button"
          onClick={() => onChange(k)}
          className={`rounded px-2 py-0.5 text-[10px] font-medium transition-colors ${
            value === k ? 'bg-[var(--color-brand)] text-white' : 'text-ink-muted hover:text-ink'
          }`}
        >
          {KIND_LABELS[k]}
        </button>
      ))}
    </div>
  );
}
