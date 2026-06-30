import { useEffect, useRef, useState } from 'react';
import { AnimatePresence, motion } from 'motion/react';
import { Languages, Check } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { SUPPORTED } from '@/i18n';

/** Compact locale picker (English / Italiano), persisted via the detector. */
export function LanguageSwitcher() {
  const { t, i18n } = useTranslation();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    window.addEventListener('mousedown', onClick);
    return () => window.removeEventListener('mousedown', onClick);
  }, [open]);

  const current = i18n.resolvedLanguage || i18n.language;

  return (
    <div ref={ref} className="relative">
      <button
        title={t('common.language')}
        onClick={() => setOpen((v) => !v)}
        className="flex items-center rounded-xl px-2 py-1.5 text-[var(--color-muted)] transition-colors hover:bg-[var(--color-elevated)] hover:text-[var(--color-text)]"
      >
        <Languages className="size-4" />
      </button>
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: -4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -4 }}
            transition={{ duration: 0.12 }}
            className="bb-solid absolute right-0 top-full z-50 mt-1 w-36 overflow-hidden rounded-lg p-1"
          >
            {SUPPORTED.map((lang) => (
              <button
                key={lang.code}
                onClick={() => {
                  void i18n.changeLanguage(lang.code);
                  setOpen(false);
                }}
                className="flex w-full items-center gap-2 rounded-md px-2.5 py-1.5 text-left text-sm text-[var(--color-muted)] transition-colors hover:bg-[var(--color-elevated)] hover:text-[var(--color-text)]"
              >
                <Check
                  className={
                    'size-3.5 ' +
                    (current?.startsWith(lang.code) ? 'text-[var(--color-accent)]' : 'opacity-0')
                  }
                />
                {lang.label}
              </button>
            ))}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
