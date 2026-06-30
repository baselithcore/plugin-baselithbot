import { useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { useBrain } from '@/store';
import { wordCount, readingMinutes } from '@/lib/outline';

/** Thin editor footer: word count, reading time and the note's last-saved time. */
export function StatusBar() {
  const { t } = useTranslation();
  const active = useBrain((s) => s.active);
  const stats = useMemo(() => {
    const words = wordCount(active?.body ?? '');
    return { words, minutes: readingMinutes(words) };
  }, [active?.body]);

  if (!active) return null;
  const saved = active.updated ? new Date(active.updated).toLocaleString() : null;

  return (
    <footer className="flex items-center gap-3 border-t border-[var(--color-border)] px-5 py-1.5 text-[11px] text-[var(--color-faint)]">
      <span>{t('status.words', { count: stats.words })}</span>
      {stats.minutes > 0 && <span>· {t('status.read', { count: stats.minutes })}</span>}
      {saved && <span className="ml-auto">{t('status.saved', { time: saved })}</span>}
    </footer>
  );
}
