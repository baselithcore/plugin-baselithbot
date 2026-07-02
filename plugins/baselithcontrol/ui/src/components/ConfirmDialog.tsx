import { useEffect, useRef } from 'react';
import { AnimatePresence, motion } from 'motion/react';
import { useTranslation } from 'react-i18next';
import { HelpCircle } from 'lucide-react';
import { spring } from '@/lib/motion';
import { useUiStore } from '@/store/useUiStore';

// Accessible, themed confirmation modal driven by useUiStore.ask(). Escape
// cancels; Enter confirms only when focus is not on a button (a focused Cancel
// must activate natively, not confirm). Tab is trapped inside the dialog and
// focus returns to the previously focused element on close.
export function ConfirmDialog() {
  const { t } = useTranslation();
  const confirm = useUiStore((s) => s.confirm);
  const resolve = useUiStore((s) => s.resolveConfirm);
  const panelRef = useRef<HTMLDivElement>(null);

  // Restore focus to whatever was focused before the dialog opened.
  useEffect(() => {
    if (!confirm) return;
    const previous = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    return () => previous?.focus();
  }, [confirm]);

  useEffect(() => {
    if (!confirm) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        resolve(false);
        return;
      }
      if (e.key === 'Enter') {
        // Only treat Enter as "confirm" when focus is NOT on a button — a
        // focused button (e.g. Cancel) uses its native activation instead.
        if (!(document.activeElement instanceof HTMLButtonElement)) resolve(true);
        return;
      }
      if (e.key === 'Tab') {
        // Focus trap: cycle Tab/Shift+Tab within the dialog's controls.
        const nodes = panelRef.current?.querySelectorAll<HTMLElement>('button:not([disabled])');
        if (!nodes || nodes.length === 0) return;
        const first = nodes[0];
        const last = nodes[nodes.length - 1];
        const active = document.activeElement;
        const inside = active instanceof HTMLElement && panelRef.current?.contains(active);
        if (e.shiftKey && (active === first || !inside)) {
          e.preventDefault();
          last.focus();
        } else if (!e.shiftKey && (active === last || !inside)) {
          e.preventDefault();
          first.focus();
        }
      }
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
        >
          <motion.div
            ref={panelRef}
            className="glass relative w-full max-w-sm rounded-xl p-6"
            style={{ boxShadow: 'var(--shadow-pop)' }}
            initial={{ opacity: 0, scale: 0.96, y: 12 }}
            animate={{ opacity: 1, scale: 1, y: 0, transition: spring }}
            exit={{ opacity: 0, scale: 0.96, y: 12 }}
            onClick={(e) => e.stopPropagation()}
            role="dialog"
            aria-modal="true"
            aria-labelledby="confirm-dialog-title"
            aria-describedby="confirm-dialog-message"
          >
            <div className="flex gap-3.5">
              <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-[var(--accent-soft)] accent-ring t-accent">
                <HelpCircle className="h-5 w-5" />
              </span>
              <div className="flex-1">
                <h3 id="confirm-dialog-title" className="text-[14px] font-semibold t-primary">
                  {t('confirm.title')}
                </h3>
                <p id="confirm-dialog-message" className="mt-1.5 text-[13px] leading-relaxed t-dim">
                  {confirm.message}
                </p>
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
