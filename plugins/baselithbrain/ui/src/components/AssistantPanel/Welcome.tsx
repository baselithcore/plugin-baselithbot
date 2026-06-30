import { motion } from 'motion/react';
import { useTranslation } from 'react-i18next';
import { MessageSquareText } from 'lucide-react';
import { itemVariants, listVariants } from '@/lib/motion';

/** Empty-thread hero with a few seed prompts. */
export function Welcome({ onAsk }: { onAsk: (q: string) => void }) {
  const { t } = useTranslation();
  const EXAMPLES = [t('welcome.ex1'), t('welcome.ex2'), t('welcome.ex3')];
  return (
    <div className="space-y-4 py-8 text-center">
      <motion.div
        initial={{ opacity: 0, y: 4 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.16, ease: [0.22, 1, 0.36, 1] }}
        className="bb-glass mx-auto flex size-11 items-center justify-center rounded-xl text-[var(--color-accent)]"
      >
        <MessageSquareText className="size-5" />
      </motion.div>
      <div>
        <p className="text-base font-semibold text-[var(--color-text)]">{t('welcome.title')}</p>
        <p className="mx-auto mt-1 max-w-xs text-xs text-[var(--color-muted)]">
          {t('welcome.body')}
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
