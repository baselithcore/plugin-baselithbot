import { AnimatePresence, motion } from 'framer-motion';
import { BookMarked, Check, ChevronDown } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';
import { cn } from '../lib/cn';

export interface EditionOption {
  id: string;
  label: string;
  edizione: string;
  edizioneIso: string;
  stato: 'vigente' | 'superata' | 'abrogata';
  note?: string;
}

export const ALL_EDITIONS_ID = '__all__';

interface Props {
  editions: EditionOption[];
  value: string;
  onChange: (id: string) => void;
}

/**
 * Dropdown in header per scegliere l'edizione di riferimento delle risposte.
 * Valore speciale: `__all__` = nessun filtro (default).
 */
export function EditionSelector({ editions, value, onChange }: Props) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onClick = (e: MouseEvent) => {
      if (!ref.current?.contains(e.target as Node)) setOpen(false);
    };
    const onEsc = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setOpen(false);
    };
    window.addEventListener('mousedown', onClick);
    window.addEventListener('keydown', onEsc);
    return () => {
      window.removeEventListener('mousedown', onClick);
      window.removeEventListener('keydown', onEsc);
    };
  }, [open]);

  const selected = editions.find((e) => e.id === value) ?? null;
  const buttonLabel = selected
    ? `${selected.label} · Ed. ${selected.edizione}`
    : 'Tutte le edizioni';

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => setOpen((v) => !v)}
        className={cn(
          'focus-ring inline-flex items-center gap-1.5 rounded-full px-2.5 py-1',
          'text-xs font-medium text-ink-muted',
          'bg-[var(--color-canvas-raised)] border border-[var(--color-border)]',
          'hover:border-[var(--color-brand-ring)] hover:text-ink transition-colors'
        )}
        aria-haspopup="listbox"
        aria-expanded={open}
        title="seleziona edizione polizza di riferimento"
      >
        <BookMarked size={11} className="text-[var(--color-brand)]" />
        <span className="hidden sm:inline truncate max-w-[220px]">{buttonLabel}</span>
        <span className="sm:hidden">Ed.</span>
        <ChevronDown size={11} className={cn('transition-transform', open && 'rotate-180')} />
      </button>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: -4, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -4, scale: 0.98 }}
            transition={{ duration: 0.12 }}
            role="listbox"
            className={cn(
              'absolute right-0 top-full mt-1.5 w-[280px] z-40',
              'rounded-xl border border-[var(--color-border)] bg-[var(--color-canvas-raised)]',
              'shadow-lg py-1'
            )}
          >
            <Option
              selected={value === ALL_EDITIONS_ID}
              onPick={() => {
                onChange(ALL_EDITIONS_ID);
                setOpen(false);
              }}
              primary="Tutte le edizioni"
              secondary="Nessun filtro — retrieval su tutte le fonti"
            />
            <div className="h-px bg-[var(--color-border)] my-1 mx-2" />
            {editions.map((e) => (
              <Option
                key={e.id}
                selected={value === e.id}
                onPick={() => {
                  onChange(e.id);
                  setOpen(false);
                }}
                primary={`${e.label} · Ed. ${e.edizione}`}
                secondary={e.note ?? e.edizioneIso}
                stato={e.stato}
              />
            ))}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

function Option({
  selected,
  onPick,
  primary,
  secondary,
  stato,
}: {
  selected: boolean;
  onPick: () => void;
  primary: string;
  secondary: string;
  stato?: 'vigente' | 'superata' | 'abrogata';
}) {
  return (
    <button
      role="option"
      aria-selected={selected}
      onClick={onPick}
      className={cn(
        'focus-ring w-full text-left px-3 py-2 flex items-start gap-2',
        'hover:bg-[var(--color-surface)] transition-colors'
      )}
    >
      <Check
        size={13}
        className={cn(
          'mt-0.5 shrink-0 text-[var(--color-brand)]',
          selected ? 'opacity-100' : 'opacity-0'
        )}
      />
      <div className="min-w-0 flex-1">
        <div className="text-xs font-medium text-ink flex items-center gap-1.5">
          <span className="truncate">{primary}</span>
          {stato === 'superata' && (
            <span className="chip !px-1.5 !py-0 !text-[9px] !bg-[var(--color-warning)]/15 !text-[var(--color-warning)] !border-transparent">
              superata
            </span>
          )}
          {stato === 'vigente' && (
            <span className="chip !px-1.5 !py-0 !text-[9px] !bg-[var(--color-success)]/15 !text-[var(--color-success)] !border-transparent">
              vigente
            </span>
          )}
          {stato === 'abrogata' && (
            <span className="chip !px-1.5 !py-0 !text-[9px] !bg-[var(--color-danger)]/15 !text-[var(--color-danger)] !border-transparent">
              abrogata
            </span>
          )}
        </div>
        <div className="text-[10px] text-ink-subtle truncate">{secondary}</div>
      </div>
    </button>
  );
}
