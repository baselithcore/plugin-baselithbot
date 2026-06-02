import clsx from 'clsx';
import { Mic, Send } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';

interface ComposerProps {
  pending: boolean;
  recording: boolean;
  onSubmitText: (text: string) => void;
  onToggleMic: () => void;
}

export function Composer({ pending, recording, onSubmitText, onToggleMic }: ComposerProps) {
  const [value, setValue] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);

  // Auto-resize the textarea up to a cap.
  useEffect(() => {
    const ta = textareaRef.current;
    if (!ta) return;
    ta.style.height = 'auto';
    ta.style.height = `${Math.min(ta.scrollHeight, 180)}px`;
  }, [value]);

  // Focus on mount so the penitent can start typing immediately.
  useEffect(() => {
    textareaRef.current?.focus();
  }, []);

  const submit = () => {
    const trimmed = value.trim();
    if (!trimmed || pending) return;
    onSubmitText(trimmed);
    setValue('');
  };

  return (
    <section
      className={clsx(
        'grid grid-cols-[1fr_auto] items-end gap-3 rounded-2xl border bg-surface-2 p-3 transition-colors',
        'border-gold-subtle focus-within:border-gold-medium'
      )}
    >
      <textarea
        ref={textareaRef}
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            submit();
          }
        }}
        disabled={pending}
        rows={1}
        placeholder="Parla al sacerdote…"
        aria-label="Confessa qui i tuoi peccati"
        autoComplete="off"
        className="min-h-[48px] max-h-[180px] resize-none rounded-lg bg-transparent p-3 font-sans text-[0.98rem] leading-relaxed text-parchment outline-none placeholder:font-serif placeholder:text-lg placeholder:italic placeholder:text-ash"
      />

      <div className="flex items-center gap-2">
        <button
          type="button"
          aria-label={recording ? 'Ferma registrazione' : 'Registra audio'}
          aria-pressed={recording}
          onClick={onToggleMic}
          disabled={pending && !recording}
          className={clsx(
            'grid h-11 w-11 place-items-center rounded-full border transition-all duration-200',
            recording
              ? 'animate-mic-pulse border-crimson-glow bg-crimson text-parchment'
              : 'border-gold-subtle bg-surface-1 text-parchment-soft hover:border-gold-medium hover:bg-surface-3 hover:text-parchment',
            pending && !recording && 'cursor-not-allowed opacity-40'
          )}
        >
          <Mic className="h-5 w-5" strokeWidth={1.8} />
        </button>

        <button
          type="button"
          aria-label="Invia parola al sacerdote"
          onClick={submit}
          disabled={pending || !value.trim()}
          className="grid h-11 w-11 place-items-center rounded-full border border-gold bg-gradient-to-b from-gold-bright to-gold-deep text-void shadow-[0_0_16px_rgba(201,168,106,0.3)] transition-shadow duration-300 hover:shadow-glow-gold-strong disabled:cursor-not-allowed disabled:opacity-40"
        >
          <Send className="h-5 w-5" strokeWidth={2} />
        </button>
      </div>

      <div className="col-span-full mt-1 flex items-center justify-between px-2 text-[0.65rem] uppercase tracking-[0.16em] text-ash">
        <span>
          <kbd className="rounded border border-gold-subtle bg-surface-2 px-1.5 py-0.5 text-[0.6rem] tracking-wider">
            Invio
          </kbd>{' '}
          invia ·{' '}
          <kbd className="rounded border border-gold-subtle bg-surface-2 px-1.5 py-0.5 text-[0.6rem] tracking-wider">
            ⇧ Invio
          </kbd>{' '}
          a capo ·{' '}
          <kbd className="rounded border border-gold-subtle bg-surface-2 px-1.5 py-0.5 text-[0.6rem] tracking-wider">
            Spazio
          </kbd>{' '}
          registra
        </span>
      </div>
    </section>
  );
}
