import { AnimatePresence, motion } from 'framer-motion';
import { useEffect } from 'react';

interface ToastProps {
  message: string | null;
  onDismiss: () => void;
  level?: 'info' | 'err';
}

export function Toast({ message, onDismiss, level = 'info' }: ToastProps) {
  useEffect(() => {
    if (!message) return;
    const t = setTimeout(onDismiss, 4200);
    return () => clearTimeout(t);
  }, [message, onDismiss]);

  return (
    <AnimatePresence>
      {message && (
        <motion.div
          role="alert"
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: 6 }}
          transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
          className={
            'fixed bottom-6 left-1/2 z-[60] -translate-x-1/2 rounded-full border bg-apse px-5 py-3 text-[0.85rem] tracking-wide text-parchment shadow-deep ' +
            (level === 'err' ? 'border-[rgba(196,64,86,0.5)]' : 'border-gold-medium')
          }
        >
          {message}
        </motion.div>
      )}
    </AnimatePresence>
  );
}
