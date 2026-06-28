import { useTranslation } from 'react-i18next';
import { Radio } from 'lucide-react';
import { useNews } from '@/hooks/useNews';
import { NewsTickerItem } from './Item';
import type { NewsItem } from '@/types';

// One scrolling marquee of public AI/tech/cyber headlines for the dashboard
// home. A single track holds the items twice; the CSS animates it by
// translateX(-50%) — exactly one copy width — so the loop is seamless. The
// duplicate group is aria-hidden and collapses under reduced-motion (where the
// strip becomes a manually-scrollable row instead — see index.css).
function Group({ items, hidden }: { items: NewsItem[]; hidden?: boolean }) {
  return (
    <div className="blc-news-group" aria-hidden={hidden || undefined}>
      {items.map((item, i) => (
        <NewsTickerItem key={`${hidden ? 'b' : 'a'}-${i}-${item.url}`} item={item} />
      ))}
    </div>
  );
}

export function NewsTicker() {
  const { t } = useTranslation();
  const { items, loading, stale } = useNews();

  // Nothing to show (feeds disabled/unreachable, or first load) → render no
  // strip at all, so the dashboard never carries an empty placeholder bar.
  if (!items.length) {
    if (loading) {
      return (
        <div className="blc-news shimmer" aria-busy="true" aria-live="polite">
          <span className="blc-news-badge">
            <Radio className="h-3.5 w-3.5" />
            {t('news.badge')}
          </span>
          <span className="blc-news-loading">{t('news.loading')}</span>
        </div>
      );
    }
    return null;
  }

  // Scale the loop duration to content length so the scroll *speed* stays
  // constant regardless of how many headlines merged in. A calm ~10s/item
  // (floor 60s) keeps it comfortably readable — news tickers read best slow;
  // hover/focus pauses it entirely for click-through.
  const duration = `${Math.max(60, items.length * 10)}s`;

  return (
    <section
      className="blc-news"
      aria-label={t('news.aria')}
      style={{ ['--blc-news-duration' as string]: duration }}
    >
      <span className="blc-news-badge" title={stale ? t('news.stale') : undefined}>
        <Radio className="h-3.5 w-3.5" />
        {t('news.badge')}
        {stale && <span className="blc-news-stale" aria-hidden="true" />}
      </span>
      <div className="blc-news-viewport">
        <div className="blc-news-track">
          <Group items={items} />
          <Group items={items} hidden />
        </div>
      </div>
    </section>
  );
}
