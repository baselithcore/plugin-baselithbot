import clsx from 'clsx';
import { AnimatePresence, motion } from 'framer-motion';
import { useEffect, useRef } from 'react';
import { PHASE_LABELS } from '../lib/phases';
import type { DialogueTurn } from '../lib/types';
import { ConfessorAudio } from './ConfessorAudio';

interface DialogueProps {
  turns: DialogueTurn[];
  thinking: boolean;
}

export function Dialogue({ turns, thinking }: DialogueProps) {
  const scrollRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const node = scrollRef.current;
    if (!node) return;
    requestAnimationFrame(() => {
      node.scrollTop = node.scrollHeight;
    });
  }, [turns.length, thinking]);

  return (
    <div
      ref={scrollRef}
      aria-live="polite"
      aria-atomic="false"
      className="nave-scroll flex flex-col gap-4 overflow-y-auto px-2"
    >
      <AnimatePresence initial={false}>
        {turns.map((t) => (
          <TurnBubble key={t.id} turn={t} />
        ))}
      </AnimatePresence>

      {thinking && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="self-start flex gap-2 px-5 py-4 font-serif italic text-ash"
        >
          Il sacerdote riflette
          <span className="inline-flex items-end gap-1" aria-hidden>
            <Dot delay={0} />
            <Dot delay={0.2} />
            <Dot delay={0.4} />
          </span>
        </motion.div>
      )}
    </div>
  );
}

function TurnBubble({ turn }: { turn: DialogueTurn }) {
  const isConfessor = turn.speaker === 'confessor';
  const isAbsolution = turn.phase === 'ASSOLUZIONE';
  const isRefusal = turn.phase === 'INVITO_RIFLESSIONE';

  const chipLabel = isConfessor
    ? turn.phase
      ? PHASE_LABELS[turn.phase] || 'Rito'
      : 'Sacerdote'
    : 'Tu';

  return (
    <motion.article
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
      className={clsx('flex max-w-[78%] flex-col gap-2', isConfessor ? 'self-start' : 'self-end')}
    >
      <span
        className={clsx(
          'inline-flex items-center gap-2 pl-2 text-[0.6rem] font-medium uppercase tracking-[0.22em]',
          isRefusal ? 'text-crimson-glow' : isConfessor ? 'text-gold' : 'text-ash'
        )}
      >
        <span
          aria-hidden
          className={clsx(
            'h-1 w-1 rounded-full',
            isRefusal
              ? 'bg-crimson-glow shadow-[0_0_6px_#c44056]'
              : isConfessor
                ? 'bg-gold shadow-[0_0_6px_#c9a86a]'
                : 'bg-ash'
          )}
        />
        {chipLabel}
      </span>

      <div
        className={clsx(
          'rounded-2xl px-5 py-4 leading-relaxed',
          isConfessor
            ? 'confessor-bubble border border-gold-subtle bg-gradient-to-b from-surface-3 to-surface-2 font-serif text-base italic text-parchment sm:text-lg'
            : 'border border-gold-subtle bg-surface-1 font-sans text-[0.96rem] text-parchment-soft',
          isAbsolution &&
            'border-gold-strong bg-gradient-to-br from-[rgba(232,201,138,0.12)] to-[rgba(201,168,106,0.06)] text-gold-bright shadow-glow-gold',
          isRefusal &&
            'border-[rgba(196,64,86,0.35)] bg-gradient-to-b from-[rgba(196,64,86,0.08)] to-[rgba(139,26,42,0.05)] text-parchment'
        )}
      >
        {turn.text}
      </div>

      {isConfessor && turn.audioBase64 ? (
        <ConfessorAudio audioBase64={turn.audioBase64} audioMime={turn.audioMime ?? null} />
      ) : null}
    </motion.article>
  );
}

function Dot({ delay }: { delay: number }) {
  return (
    <motion.span
      className="h-1 w-1 rounded-full bg-gold"
      animate={{ y: [0, -3, 0], opacity: [0.3, 1, 0.3] }}
      transition={{
        duration: 1.4,
        ease: [0.65, 0, 0.35, 1],
        repeat: Infinity,
        delay,
      }}
    />
  );
}
