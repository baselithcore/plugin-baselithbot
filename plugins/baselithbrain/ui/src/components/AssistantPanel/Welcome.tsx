import { motion } from 'motion/react';
import { Sparkles } from 'lucide-react';
import { itemVariants, listVariants } from '@/lib/motion';

const EXAMPLES = [
  'What connects atomic notes and LYT?',
  'Summarize my PKM notes',
  'What should I write about next?',
];

/** Empty-thread hero with a few seed prompts. */
export function Welcome({ onAsk }: { onAsk: (q: string) => void }) {
  return (
    <div className="space-y-4 py-8 text-center">
      <motion.div
        initial={{ scale: 0.7, opacity: 0, rotate: -8 }}
        animate={{ scale: 1, opacity: 1, rotate: 0 }}
        transition={{ type: 'spring', stiffness: 300, damping: 18 }}
        className="bb-gradient bb-btn-glow mx-auto flex size-12 items-center justify-center rounded-2xl text-white"
      >
        <Sparkles className="size-5" />
      </motion.div>
      <div>
        <p className="bb-gradient-text text-base font-semibold">Chat with your knowledge</p>
        <p className="mx-auto mt-1 max-w-xs text-xs text-[var(--color-muted)]">
          Answers are grounded in your vault and cite the notes they use. This thread remembers what
          you discussed.
        </p>
      </div>
      <motion.div
        variants={listVariants}
        initial="hidden"
        animate="show"
        className="flex flex-col items-center gap-2 pt-1"
      >
        {EXAMPLES.map((e) => (
          <motion.button
            key={e}
            variants={itemVariants}
            whileHover={{ scale: 1.03 }}
            whileTap={{ scale: 0.97 }}
            onClick={() => onAsk(e)}
            className="rounded-full border border-[var(--color-border)] bg-[var(--color-surface)]/60 px-3.5 py-1.5 text-xs text-[var(--color-muted)] transition hover:border-[var(--color-accent)] hover:text-[var(--color-text)]"
          >
            {e}
          </motion.button>
        ))}
      </motion.div>
    </div>
  );
}
