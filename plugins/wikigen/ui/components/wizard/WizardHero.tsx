import { motion } from 'framer-motion';
import { RefreshCw, ShieldCheck } from 'lucide-react';
import { IconButton } from '../ui';

interface Props {
  progressPct: number;
  onRefresh: () => void;
}

/**
 * Branded hero rendered above the wizard panel in the screen variant. Shows
 * the headline, supporting copy and a live progress chip; the chip + refresh
 * button only appear on `lg` viewports to avoid header crowding on mobile.
 */
export function WizardHero({ progressPct, onRefresh }: Props) {
  return (
    <motion.header
      initial={{ opacity: 0, y: -8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.18 }}
      className="relative z-10 mx-auto mb-4 flex w-full max-w-6xl items-center justify-between gap-4"
    >
      <div className="min-w-0">
        <div className="inline-flex items-center gap-2 rounded-full border border-[var(--color-border)] bg-[var(--color-canvas-raised)] px-3 py-1 text-[10px] font-semibold uppercase text-ink-muted shadow-sm">
          <ShieldCheck size={11} className="text-[var(--color-brand)]" />
          Setup enterprise
        </div>
        <h1 className="mt-2 text-2xl font-semibold text-ink sm:text-3xl">
          Configura la tua knowledge base
        </h1>
        <p className="mt-1 max-w-2xl text-[12.5px] leading-relaxed text-ink-muted">
          Identità, archivio, aspetto e primi documenti — guidati passo dopo passo con riepilogo
          finale prima di confermare.
        </p>
      </div>
      <div className="hidden shrink-0 items-center gap-2 lg:flex">
        <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-canvas-raised)] px-3 py-2 shadow-sm">
          <div className="text-[10px] uppercase text-ink-subtle">Progresso</div>
          <div className="mt-0.5 text-sm font-semibold tabular-nums text-ink">{progressPct}%</div>
        </div>
        <IconButton
          icon={RefreshCw}
          aria-label="aggiorna elenco wiki"
          size="lg"
          emphasis="outline"
          onClick={onRefresh}
        />
      </div>
    </motion.header>
  );
}
