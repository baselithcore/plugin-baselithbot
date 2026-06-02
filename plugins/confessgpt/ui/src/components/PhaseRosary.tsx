import clsx from 'clsx';
import { motion } from 'framer-motion';
import { RITE_CHAIN, isRefusalBranch, phaseIndex } from '../lib/phases';
import type { RitePhase } from '../lib/types';

interface PhaseRosaryProps {
  current: RitePhase;
}

// Rosary-bead style progress indicator. Beads light progressively as
// the rite advances. A refusal branch (INVITO_RIFLESSIONE) recolors
// the absolution bead crimson and relabels it "Riflessione".
export function PhaseRosary({ current }: PhaseRosaryProps) {
  const refusal = isRefusalBranch(current);
  const activeIdx = refusal
    ? RITE_CHAIN.findIndex((p) => p.id === 'ASSOLUZIONE')
    : phaseIndex(current);

  return (
    <nav
      aria-label="Fasi del sacramento"
      className="bead-line flex items-center justify-between gap-2 rounded-2xl border border-gold-subtle bg-surface-1 px-3 py-4 sm:px-4"
    >
      {RITE_CHAIN.map((p, i) => {
        let state: 'done' | 'active' | 'idle' | 'refusal' = 'idle';
        if (refusal && p.id === 'ASSOLUZIONE') state = 'refusal';
        else if (i < activeIdx) state = 'done';
        else if (i === activeIdx) state = 'active';

        const label = refusal && p.id === 'ASSOLUZIONE' ? 'Riflessione' : p.label;

        return (
          <div
            key={p.id}
            className="relative z-10 flex min-w-[60px] flex-1 flex-col items-center gap-2 text-center"
          >
            <motion.span
              aria-hidden
              animate={
                state === 'active'
                  ? { scale: 1.4 }
                  : state === 'refusal'
                    ? { scale: 1.2 }
                    : { scale: 1 }
              }
              transition={{ duration: 0.6, ease: [0.65, 0, 0.35, 1] }}
              className={clsx(
                'h-3.5 w-3.5 rounded-full border transition-colors duration-700',
                state === 'idle' && 'border-gold-medium bg-nave',
                state === 'done' && 'border-gold-deep bg-gold-deep',
                state === 'active' && 'animate-flicker border-gold-bright bg-gold-bright',
                state === 'refusal' && 'border-crimson-glow bg-crimson-glow shadow-glow-crimson'
              )}
            />
            <span
              className={clsx(
                'whitespace-nowrap text-[0.55rem] font-medium uppercase tracking-[0.14em] transition-colors duration-700 sm:text-[0.62rem] sm:tracking-[0.18em]',
                state === 'idle' && 'text-ash',
                state === 'done' && 'text-parchment-soft',
                state === 'active' && 'font-semibold text-gold-bright',
                state === 'refusal' && 'text-crimson-glow'
              )}
            >
              {label}
            </span>
          </div>
        );
      })}
    </nav>
  );
}
