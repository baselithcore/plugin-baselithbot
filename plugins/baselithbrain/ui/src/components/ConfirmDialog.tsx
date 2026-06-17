import { useEffect, useState } from 'react';
import { AnimatePresence, motion } from 'motion/react';
import { AlertTriangle } from 'lucide-react';
import { backdropVariants, popVariants } from '@/lib/motion';

/**
 * In-app confirmation modal.
 *
 * Replaces ``window.confirm`` which is silently suppressed in embedded
 * webviews (native app shells, in-IDE browsers) — there it returns false, so
 * destructive actions gated on it never run. This is a promise-based dialog:
 * call ``askConfirm(message)`` and await the boolean. ``<ConfirmHost/>`` must
 * be mounted once at the app root.
 */

interface Pending {
  message: string;
  resolve: (ok: boolean) => void;
}

let openDialog: ((p: Pending) => void) | null = null;

/** Ask the user to confirm. Resolves true on confirm, false on cancel/dismiss. */
export function askConfirm(message: string): Promise<boolean> {
  return new Promise((resolve) => {
    if (!openDialog) {
      // Host not mounted — fail closed (no accidental deletes).
      resolve(false);
      return;
    }
    openDialog({ message, resolve });
  });
}

/** Singleton host that renders the active confirmation, if any. */
export function ConfirmHost() {
  const [pending, setPending] = useState<Pending | null>(null);

  useEffect(() => {
    openDialog = (p) => setPending(p);
    return () => {
      openDialog = null;
    };
  }, []);

  useEffect(() => {
    if (!pending) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') settle(false);
      else if (e.key === 'Enter') settle(true);
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pending]);

  function settle(ok: boolean) {
    pending?.resolve(ok);
    setPending(null);
  }

  return (
    <AnimatePresence>
      {pending && (
        <motion.div
          variants={backdropVariants}
          initial="hidden"
          animate="show"
          exit="exit"
          className="fixed inset-0 z-50 flex items-center justify-center bg-[var(--color-overlay)] backdrop-blur-md"
          onClick={() => settle(false)}
        >
          <motion.div
            role="alertdialog"
            aria-modal="true"
            variants={popVariants}
            initial="hidden"
            animate="show"
            exit="exit"
            onClick={(e) => e.stopPropagation()}
            className="bb-glass w-[min(90vw,25rem)] rounded-2xl p-6 shadow-2xl"
          >
            <div className="flex items-start gap-3.5">
              <span className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-[hsl(353_74%_54%_/_0.12)] text-[var(--color-danger)]">
                <AlertTriangle className="size-5" />
              </span>
              <p className="pt-1.5 text-sm leading-relaxed text-[var(--color-text)]">
                {pending.message}
              </p>
            </div>
            <div className="mt-6 flex justify-end gap-2">
              <button
                onClick={() => settle(false)}
                className="rounded-xl px-3.5 py-2 text-sm text-[var(--color-muted)] transition hover:bg-[var(--color-elevated)]"
              >
                Cancel
              </button>
              <motion.button
                autoFocus
                whileTap={{ scale: 0.96 }}
                onClick={() => settle(true)}
                className="rounded-xl bg-[var(--color-danger)] px-3.5 py-2 text-sm font-medium text-white shadow-[0_6px_18px_-6px_hsl(353_74%_54%_/_0.6)] transition hover:brightness-110"
              >
                Delete
              </motion.button>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
