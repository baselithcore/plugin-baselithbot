import { useLayoutEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Radio } from 'lucide-react';
import { useNews } from '@/hooks/useNews';
import { NewsTickerItem } from './Item';
import type { NewsItem } from '@/types';

// Pixels/second the strip travels. A *constant* speed (independent of how many
// headlines merged in) is the right model for a marquee: the old item-count
// heuristic made 40 items crawl for ~6½ min per loop, so a glance only ever saw
// the leading few — they looked "stuck". ~70 px/s reads calmly while clearly
// moving. Hover/focus still pauses it for click-through (see index.css).
const SPEED_PX_PER_SEC = 70;
const MIN_DURATION_SEC = 30; // floor so a short list never whips past too fast

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

// Measure one group's rendered width and derive a duration that yields a
// constant scroll speed. The track holds two identical groups and the keyframe
// translates it -50% (exactly one group width), so distance = scrollWidth / 2.
// A ResizeObserver recomputes on layout/content/viewport changes; falls back to
// a sane default until measured (and whenever the strip can't be measured).
function useMarqueeDuration(deps: unknown) {
  const trackRef = useRef<HTMLDivElement>(null);
  const [duration, setDuration] = useState('60s');
  useLayoutEffect(() => {
    const el = trackRef.current;
    if (!el) return;
    const measure = () => {
      const groupWidth = el.scrollWidth / 2;
      if (groupWidth > 0) {
        setDuration(`${Math.max(MIN_DURATION_SEC, groupWidth / SPEED_PX_PER_SEC)}s`);
      }
    };
    measure();
    const ro = new ResizeObserver(measure);
    ro.observe(el);
    return () => ro.disconnect();
  }, [deps]);
  return { trackRef, duration };
}

export function NewsTicker() {
  const { t } = useTranslation();
  const { items, loading, stale } = useNews();
  const { trackRef, duration } = useMarqueeDuration(items);

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
        <div className="blc-news-track" ref={trackRef}>
          <Group items={items} />
          <Group items={items} hidden />
        </div>
      </div>
    </section>
  );
}
