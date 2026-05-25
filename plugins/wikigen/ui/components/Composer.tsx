import { ArrowUp, Square } from 'lucide-react';
import { useRef, useState, type KeyboardEvent } from 'react';
import { useAutoResize } from '../hooks/useAutoResize';
import { cn } from '../lib/cn';

interface Props {
  onSend: (text: string) => void;
  onStop?: () => void;
  isStreaming: boolean;
  placeholder?: string;
}

const MAX_CHARS = 4000;

export function Composer({
  onSend,
  onStop,
  isStreaming,
  placeholder = 'Chiedi qualcosa alla tua wiki…',
}: Props) {
  const [value, setValue] = useState('');
  const ref = useRef<HTMLTextAreaElement>(null);
  useAutoResize(ref, value, { maxHeight: 260 });

  const trimmed = value.trim();
  const canSend = trimmed.length > 0 && !isStreaming;
  const overLimit = value.length > MAX_CHARS;

  const submit = () => {
    if (!canSend || overLimit) return;
    onSend(trimmed);
    setValue('');
  };

  const onKey = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) {
      e.preventDefault();
      submit();
    }
  };

  return (
    <div className="pb-5 px-4 sm:px-6">
      <div className="mx-auto max-w-3xl">
        <div
          className={cn(
            'relative z-10 rounded-2xl transition-[border-color,box-shadow] duration-[var(--duration-base)]',
            'bg-[var(--color-canvas-raised)] border border-[var(--color-border-strong)]',
            'shadow-[var(--shadow-lg)]',
            'focus-within:border-[var(--color-brand)] focus-within:shadow-[var(--shadow-glow)]',
            isStreaming && 'gradient-border'
          )}
        >
          <textarea
            ref={ref}
            value={value}
            onChange={(e) => setValue(e.target.value)}
            onKeyDown={onKey}
            placeholder={placeholder}
            rows={1}
            spellCheck
            aria-label="domanda"
            aria-describedby="composer-help"
            aria-invalid={overLimit || undefined}
            className="resize-none w-full bg-transparent outline-none
                       px-4 pt-3.5 pb-12 text-[15px] leading-6
                       placeholder:text-ink-subtle text-ink"
            style={{ minHeight: '56px' }}
          />

          {/* toolbar bottom */}
          <div className="absolute inset-x-2 bottom-2 flex items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              {value.length > 0 && (
                <span
                  className={cn(
                    'pl-2 text-[10.5px] tabular-nums',
                    overLimit ? 'text-[var(--color-danger)] font-medium' : 'text-ink-subtle'
                  )}
                  title={overLimit ? 'messaggio troppo lungo' : 'caratteri'}
                >
                  {value.length.toLocaleString('it-IT')}
                  {overLimit && ` / ${MAX_CHARS.toLocaleString('it-IT')}`}
                </span>
              )}
            </div>

            <div className="flex items-center gap-2">
              <span className="hidden sm:inline-flex items-center gap-1 text-[10px] text-ink-subtle">
                <kbd className="rounded border border-[var(--color-border)] bg-[var(--color-surface)] px-1.5 py-0.5 font-mono text-[10px] leading-none">
                  ↵
                </kbd>
                invia
                <span className="mx-1 text-[var(--color-border-strong)]">·</span>
                <kbd className="rounded border border-[var(--color-border)] bg-[var(--color-surface)] px-1.5 py-0.5 font-mono text-[10px] leading-none">
                  ⇧ ↵
                </kbd>
                a capo
              </span>
              {isStreaming ? (
                <button
                  onClick={onStop}
                  className="focus-ring inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-semibold
                             bg-[var(--color-danger)]/15 text-[var(--color-danger)] border border-[var(--color-danger)]/40
                             hover:bg-[var(--color-danger)]/25 transition-colors"
                  aria-label="ferma generazione"
                >
                  <Square size={11} fill="currentColor" /> Ferma
                </button>
              ) : (
                <button
                  onClick={submit}
                  disabled={!canSend || overLimit}
                  className={cn(
                    'focus-ring inline-flex items-center justify-center size-10 rounded-xl transition-[background-color,box-shadow,transform] duration-[var(--duration-fast)]',
                    'bg-[var(--color-brand)] text-white shadow-[var(--shadow-brand)]',
                    'hover:bg-[var(--color-brand-strong)] hover:scale-[1.05] active:scale-[0.94]',
                    'disabled:bg-[var(--color-surface-hover)] disabled:text-ink-subtle',
                    'disabled:cursor-not-allowed disabled:shadow-none disabled:scale-100'
                  )}
                  aria-label="invia"
                >
                  <ArrowUp size={17} strokeWidth={2.75} />
                </button>
              )}
            </div>
          </div>
        </div>
        <p
          id="composer-help"
          className="mt-2 text-center text-[10.5px] text-ink-subtle"
        >
          Risposte basate sui documenti caricati. I dati restano sul tuo computer.
        </p>
      </div>
    </div>
  );
}
