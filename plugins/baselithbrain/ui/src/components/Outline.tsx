import { useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { parseOutline } from '@/lib/outline';

/**
 * Table of contents for the active note. Parsed from the Markdown body in
 * document order, which matches the heading order rendered in `.bb-prose`, so
 * clicking row *i* scrolls to the *i*-th heading element.
 */
export function Outline({ body }: { body: string }) {
  const { t } = useTranslation();
  const items = useMemo(() => parseOutline(body), [body]);

  const scrollTo = (index: number) => {
    const headings = document.querySelectorAll<HTMLElement>('.bb-prose h1, .bb-prose h2, .bb-prose h3');
    headings[index]?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  };

  if (!items.length) {
    return <p className="px-2 py-1 text-xs text-[var(--color-faint)]">{t('rail.noHeadings')}</p>;
  }

  return (
    <div className="space-y-0.5">
      {items.map((item, i) => (
        <button
          key={item.id}
          onClick={() => scrollTo(i)}
          style={{ paddingLeft: `${(item.level - 1) * 0.75 + 0.5}rem` }}
          className="block w-full truncate rounded-md py-1 pr-2 text-left text-xs text-[var(--color-muted)] transition-colors hover:bg-[var(--color-elevated)] hover:text-[var(--color-text)]"
          title={item.text}
        >
          {item.text}
        </button>
      ))}
    </div>
  );
}
