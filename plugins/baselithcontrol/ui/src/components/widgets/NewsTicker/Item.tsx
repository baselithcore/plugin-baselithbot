import { useTranslation } from 'react-i18next';
import type { NewsCategory, NewsItem } from '@/types';

// Fixed, theme-independent accent per topic lane (mirrors the digest palette).
// Used only for the small leading dot, so contrast against any surface is fine.
const DOT: Record<NewsCategory, string> = {
  ai: '#2563eb',
  tech: '#7c3aed',
  cyber: '#e11d48',
  regulation: '#d97706',
  society: '#16a34a',
  repos: '#475569',
  general: '#64748b',
};

export function NewsTickerItem({ item }: { item: NewsItem }) {
  const { t } = useTranslation();
  const category = t(`news.cat_${item.category}`);
  return (
    <a
      href={item.url}
      target="_blank"
      rel="noopener noreferrer"
      className="blc-news-item group"
      title={`${item.source} · ${category}`}
    >
      <span
        className="blc-news-dot"
        style={{ backgroundColor: DOT[item.category] ?? DOT.general }}
        aria-hidden="true"
      />
      <span className="blc-news-source">{item.source}</span>
      <span className="blc-news-title">{item.title}</span>
    </a>
  );
}
