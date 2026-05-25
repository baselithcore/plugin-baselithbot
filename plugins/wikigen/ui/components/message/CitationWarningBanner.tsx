import { AnimatePresence, motion } from 'framer-motion';
import { AlertTriangle, ChevronRight } from 'lucide-react';
import { useState } from 'react';
import type { CitationWarning } from '../../lib/types';
import { cn } from '../../lib/cn';
import { duration, ease } from '../../lib/motion';

const REASON_LABEL: Record<string, string> = {
  unknown_folder: 'cartella inesistente nel vault',
  slug_not_in_sources: 'pagina non fra le fonti recuperate',
  malformed: 'wikilink malformato',
};

/**
 * Banner non bloccante: la risposta è comunque mostrata, ma il backend ha
 * rilevato citazioni non riconducibili al vault o alle fonti recuperate
 * per questa query. Toni warning (ambra), non error — l'utente decide
 * se rigenerare o procedere.
 */
export function CitationWarningBanner({ warning }: { warning: CitationWarning }) {
  const [open, setOpen] = useState(false);
  const count = warning.violations.length;
  return (
    <motion.div
      role="status"
      aria-live="polite"
      initial={{ opacity: 0, y: -4 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: duration.slow, ease: ease.outExpo }}
      className="mt-3 rounded-lg border border-amber-500/40 bg-amber-500/8 px-3 py-2"
    >
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="focus-ring flex w-full items-start justify-between gap-2 text-left"
        aria-expanded={open}
      >
        <div className="flex items-start gap-2">
          <AlertTriangle size={14} className="mt-0.5 shrink-0 text-amber-600" aria-hidden />
          <div className="min-w-0">
            <div className="text-xs font-semibold text-amber-900 dark:text-amber-200">
              Citazioni da verificare ({count})
            </div>
            <div className="text-[11px] text-amber-800/90 dark:text-amber-200/80">
              {warning.summary}
            </div>
          </div>
        </div>
        <ChevronRight
          size={12}
          className={cn(
            'mt-0.5 shrink-0 text-amber-700 transition-transform',
            open && 'rotate-90'
          )}
          aria-hidden
        />
      </button>
      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            // grid-template-rows trick: animate 0fr→1fr instead of height,
            // keeps content unsquashed and avoids layout thrash.
            initial={{ gridTemplateRows: '0fr', opacity: 0 }}
            animate={{ gridTemplateRows: '1fr', opacity: 1 }}
            exit={{ gridTemplateRows: '0fr', opacity: 0 }}
            transition={{ duration: duration.base, ease: ease.outQuart }}
            className="grid"
          >
            <div className="min-h-0 overflow-hidden">
              <ul className="mt-2 space-y-1 border-t border-amber-500/30 pt-2 text-[11px]">
                {warning.violations.slice(0, 10).map((v, i) => (
                  <li key={i} className="flex items-start gap-2">
                    <code className="rounded bg-amber-500/15 px-1 py-0.5 font-mono text-[10px] text-amber-900 dark:text-amber-200">
                      {v.raw}
                    </code>
                    <span className="text-amber-800/90 dark:text-amber-200/80">
                      {REASON_LABEL[v.reason] ?? v.reason}
                    </span>
                  </li>
                ))}
                {warning.violations.length > 10 && (
                  <li className="text-amber-700/80 italic">
                    + altre {warning.violations.length - 10}
                  </li>
                )}
              </ul>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
