import { useState } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { useTranslation } from 'react-i18next';
import { ChevronRight, Layers } from 'lucide-react';
import type { PluginCard as Card } from '@/types';
import { PluginCard } from '@/components/widgets/PluginCard';
import { listVariants } from '@/lib/motion';

const GRID = 'grid density-grid gap-3';

interface Props {
  cards: Card[];
  onOpen: (name: string) => void;
  canControl: boolean;
}

/**
 * Secondary, collapsed-by-default bucket for framework/infrastructure plugins
 * (manifest `control.tier: system`). Keeps the main grid focused on custom
 * feature plugins; system plugins stay one click away.
 */
export function SystemSection({ cards, onOpen, canControl }: Props) {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);

  if (cards.length === 0) return null;

  return (
    <section className="space-y-3">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        className="group flex w-full items-center gap-3 rounded-lg py-1 text-left transition hover:opacity-90"
      >
        <ChevronRight
          className={`h-4 w-4 shrink-0 t-faint transition-transform ${open ? 'rotate-90' : ''}`}
        />
        <Layers className="h-3.5 w-3.5 shrink-0 t-faint" />
        <h3 className="shrink-0 text-[12px] font-semibold uppercase tracking-wide t-dim">
          {t('section.system')}
        </h3>
        <span className="shrink-0 rounded-md border brd bg-[var(--surface-inset)] px-1.5 py-0.5 text-[11px] font-semibold tabular-nums t-faint">
          {cards.length}
        </span>
        <span className="hidden min-w-0 truncate text-[11px] t-faint sm:block">
          {t('section.system_hint')}
        </span>
        <div className="h-px flex-1 bg-[var(--border)]" />
      </button>

      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <motion.div
              variants={listVariants}
              initial="hidden"
              animate="show"
              className={`${GRID} pt-1`}
            >
              {cards.map((card) => (
                <PluginCard key={card.name} card={card} onOpen={onOpen} canControl={canControl} />
              ))}
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </section>
  );
}
