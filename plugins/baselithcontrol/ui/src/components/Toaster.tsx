import { AnimatePresence, motion } from 'motion/react';
import { X } from 'lucide-react';
import type { Tone } from '@/lib/format';
import { useUiStore } from '@/store/useUiStore';

const TONE: Record<Tone, string> = {
  neutral: 't-primary',
  success: 'border-emerald-500/30 text-emerald-500',
  warning: 'border-amber-500/30 text-amber-500',
  danger: 'border-rose-500/30 text-rose-500',
  info: 'border-sky-500/30 text-sky-500',
};

export function Toaster() {
  const toasts = useUiStore((s) => s.toasts);
  const dismiss = useUiStore((s) => s.dismissToast);

  return (
    <div
      className="pointer-events-none fixed bottom-4 right-4 z-50 flex flex-col gap-2"
      role="status"
      aria-live="polite"
    >
      <AnimatePresence>
        {toasts.map((t) => (
          <motion.div
            key={t.id}
            layout
            initial={{ opacity: 0, x: 24 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 24 }}
            style={{ boxShadow: 'var(--shadow-pop)' }}
            className={`glass pointer-events-auto flex items-center gap-3 rounded-lg border px-4 py-2.5 text-[13px] font-medium ${TONE[t.tone]}`}
          >
            <span>{t.message}</span>
            <button
              type="button"
              aria-label="dismiss"
              onClick={() => dismiss(t.id)}
              className="opacity-60 hover:opacity-100"
            >
              <X className="h-3.5 w-3.5" />
            </button>
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  );
}
