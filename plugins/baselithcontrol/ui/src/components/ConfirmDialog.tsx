import { useEffect } from 'react';
import { AnimatePresence, motion } from 'motion/react';
import { useTranslation } from 'react-i18next';
import { HelpCircle } from 'lucide-react';
import { spring } from '@/lib/motion';
import { useUiStore } from '@/store/useUiStore';

// Accessible, themed confirmation modal driven by useUiStore.ask(). Escape
// cancels, Enter confirms, focus is trapped on the confirm button.
export function ConfirmDialog() {
  const { t } = useTranslation();
  const confirm = useUiStore((s) => s.confirm);
  const resolve = useUiStore((s) => s.resolveConfirm);

  useEffect(() => {
    if (!confirm) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') resolve(false);
      if (e.key === 'Enter') resolve(true);
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [confirm, resolve]);

  return (
    <AnimatePresence>
      {confirm && (
        <motion.div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4 backdrop-blur-sm"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={() => resolve(false)}
          role="dialog"
          aria-modal="true"
        >
          <motion.div
            className="glass relative w-full max-w-sm rounded-xl p-6"
            style={{ boxShadow: 'var(--shadow-pop)' }}
            initial={{ opacity: 0, scale: 0.96, y: 12 }}
            animate={{ opacity: 1, scale: 1, y: 0, transition: spring }}
            exit={{ opacity: 0, scale: 0.96, y: 12 }}
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex gap-3.5">
              <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-[var(--accent-soft)] accent-ring t-accent">
                <HelpCircle className="h-5 w-5" />
              </span>
              <div className="flex-1">
                <h3 className="text-[14px] font-semibold t-primary">Confirm action</h3>
                <p className="mt-1.5 text-[13px] leading-relaxed t-dim">{confirm.message}</p>
              </div>
            </div>

            <div className="mt-6 flex justify-end gap-2">
              <button
                type="button"
                onClick={() => resolve(false)}
                className="rounded-lg border brd px-4 py-2 text-[13px] font-medium t-dim transition surf-hover"
              >
                {t('confirm.cancel')}
              </button>
              <button
                type="button"
                autoFocus
                onClick={() => resolve(true)}
                className="btn-primary rounded-lg px-4 py-2 text-[13px] font-semibold"
              >
                {t('confirm.ok')}
              </button>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
