import { useMemo, useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { useTranslation } from 'react-i18next';
import { Search, ArrowUpDown, LayoutGrid, List, Filter } from 'lucide-react';
import { useInventory } from '@/hooks/useInventory';
import { useCanAccessPlugin } from '@/hooks/useAccess';
import { useControlStore } from '@/store/useControlStore';
import { listVariants, pageVariants } from '@/lib/motion';
import { PluginCard } from '@/components/widgets/PluginCard';
import { CardSkeleton } from '@/components/widgets/CardSkeleton';
import { HeadBand } from '@/components/HeadBand';
import { ControlInsights } from '@/components/ControlInsights';
import { ResourcePanel } from '@/components/widgets/ResourcePanel';
import { StatusFilterBar } from '@/components/StatusFilterBar';
import { SystemSection } from '@/components/SystemSection';
import type { PluginCard as Card } from '@/types';

const GRID = 'grid density-grid gap-3';
type StateFilter = Card['state'] | 'all';

function matches(card: Card, q: string): boolean {
  if (!q) return true;
  const hay = `${card.name} ${card.description} ${card.tags.join(' ')}`.toLowerCase();
  return hay.includes(q.toLowerCase());
}

function groupBy(cards: Card[]): [string, Card[]][] {
  const groups = new Map<string, Card[]>();
  for (const c of cards) {
    const key = c.group || c.category || 'uncategorized';
    (groups.get(key) ?? groups.set(key, []).get(key)!).push(c);
  }
  return [...groups.entries()].sort(([a], [b]) => a.localeCompare(b));
}

// Custom sort helper
function sortCards(cards: Card[], sortBy: 'name' | 'status'): Card[] {
  return [...cards].sort((a, b) => {
    if (sortBy === 'status') {
      // Failed first, then Active, Discovered, Disabled
      const rank: Record<string, number> = {
        failed: 1,
        active: 2,
        discovered: 3,
        unknown: 4,
        disabled: 5,
      };
      const rA = rank[a.state] ?? 10;
      const rB = rank[b.state] ?? 10;
      if (rA !== rB) return rA - rB;
    }
    return a.name.localeCompare(b.name);
  });
}

export function Overview({ onOpen }: { onOpen: (name: string) => void }) {
  const { t } = useTranslation();
  const { loading, error } = useInventory();
  const order = useControlStore((s) => s.order);
  const plugins = useControlStore((s) => s.plugins);
  const me = useControlStore((s) => s.me);
  const connected = useControlStore((s) => s.connected);
  const eventsCount = useControlStore((s) => s.events.length);
  // Hide whole plugins the caller (or impersonated user) may not access, per the
  // central per-tab policy — not just block "Open". Default-allow for unmanaged.
  const canAccessPlugin = useCanAccessPlugin();

  const [query, setQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [selectedState, setSelectedState] = useState<StateFilter>('active');
  const [sortBy, setSortBy] = useState<'name' | 'status'>('name');
  const [isFlat, setIsFlat] = useState(true);

  const searchInputRef = useRef<HTMLInputElement>(null);

  // Focus search input on "/" keypress
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (
        e.key === '/' &&
        document.activeElement?.tagName !== 'INPUT' &&
        document.activeElement?.tagName !== 'TEXTAREA'
      ) {
        e.preventDefault();
        searchInputRef.current?.focus();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  const allCards = useMemo(
    () =>
      order
        .map((n) => plugins[n])
        .filter((c): c is Card => Boolean(c))
        .filter((c) => canAccessPlugin(c.name)),
    [order, plugins, canAccessPlugin]
  );

  // Compute unique categories (only from plugins the caller may see)
  const categories = useMemo(() => {
    const cats = new Set<string>();
    allCards.forEach((c) => {
      if (c.category) cats.add(c.category);
    });
    return ['all', ...Array.from(cats).sort()];
  }, [allCards]);

  const stateCounts = useMemo<Record<StateFilter, number>>(() => {
    const counts: Record<StateFilter, number> = {
      all: allCards.length,
      active: 0,
      discovered: 0,
      disabled: 0,
      failed: 0,
      unknown: 0,
    };
    for (const card of allCards) counts[card.state] += 1;
    return counts;
  }, [allCards]);

  // Filter and sort plugins
  const filteredAndSorted = useMemo(() => {
    let result = allCards.filter((c) => matches(c, query));

    if (selectedState !== 'all') {
      result = result.filter((c) => c.state === selectedState);
    }
    if (selectedCategory !== 'all') {
      result = result.filter((c) => c.category === selectedCategory);
    }

    return sortCards(result, sortBy);
  }, [allCards, query, selectedCategory, selectedState, sortBy]);

  // Split the tier-2 system/infrastructure plugins out of the primary grid;
  // they live in a collapsed secondary section so the grid stays focused on
  // custom feature plugins.
  const appCards = useMemo(
    () => filteredAndSorted.filter((c) => c.tier !== 'system'),
    [filteredAndSorted]
  );
  const systemCards = useMemo(
    () => filteredAndSorted.filter((c) => c.tier === 'system'),
    [filteredAndSorted]
  );

  // Grouped plugins list (application tier only — system has its own section)
  const grouped = useMemo(() => {
    return groupBy(appCards);
  }, [appCards]);

  if (error)
    return <div className="glass border-rose-500/25 p-6 text-sm text-rose-500">{error}</div>;

  if (loading && order.length === 0) {
    return (
      <div className={GRID}>
        {Array.from({ length: 8 }).map((_, i) => (
          <CardSkeleton key={i} />
        ))}
      </div>
    );
  }

  if (!loading && order.length === 0) {
    return (
      <div className="glass mx-auto mt-20 max-w-md p-8 text-center">
        <h2 className="text-base font-semibold t-primary">{t('empty.title')}</h2>
        <p className="mt-2 text-xs leading-relaxed t-dim">{t('empty.body')}</p>
      </div>
    );
  }

  const readOnly = me !== null && !me.is_admin;

  return (
    <motion.div
      variants={pageVariants}
      initial="hidden"
      animate="show"
      exit="exit"
      className="space-y-3"
    >
      {/* Page heading */}
      <div className="flex items-baseline gap-3">
        <h1 className="font-display text-[1.35rem] font-bold leading-tight tracking-tight t-primary">
          {t('nav.overview')}
        </h1>
        <p className="truncate text-[13px] t-dim">{t('app.subtitle')}</p>
      </div>

      {/* Unified metrics band: 8 KPIs (health + ops) on a single hairline grid */}
      <div className="glass overflow-hidden">
        <div className="grid grid-cols-2 gap-px bg-[var(--border)] sm:grid-cols-4 xl:grid-cols-8">
          <HeadBand cards={allCards} />
          <ControlInsights
            cards={allCards}
            connected={connected}
            eventsCount={eventsCount}
            readOnly={readOnly}
          />
        </div>
      </div>

      <ResourcePanel onOpen={onOpen} />

      {/* Plugin toolbar: search + status filter + view + sort — the control deck */}
      <div className="glass flex flex-col gap-3 p-3 lg:flex-row lg:items-center">
        <div className="relative w-full lg:max-w-xs">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 t-faint" />
          <input
            ref={searchInputRef}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={t('search.placeholder')}
            className="control-field ph-faint w-full rounded-lg py-2.5 pl-9 pr-3 text-[13px] t-primary outline-none transition focus:border-[var(--accent-border)]"
          />
        </div>

        <div className="lg:flex-1">
          <StatusFilterBar counts={stateCounts} value={selectedState} onChange={setSelectedState} />
        </div>

        <div className="flex flex-wrap items-center gap-2 lg:justify-end">
          {/* View switcher */}
          <div className="flex rounded-lg border brd bg-[var(--surface-inset)] p-0.5">
            <button
              type="button"
              onClick={() => setIsFlat(false)}
              title="Grouped view"
              aria-pressed={!isFlat}
              className={`rounded-md p-1.5 transition ${!isFlat ? 'bg-[var(--accent-soft)] t-accent' : 't-dim hover:text-[var(--text)]'}`}
            >
              <LayoutGrid className="h-4 w-4" />
            </button>
            <button
              type="button"
              onClick={() => setIsFlat(true)}
              title="Flat list view"
              aria-pressed={isFlat}
              className={`rounded-md p-1.5 transition ${isFlat ? 'bg-[var(--accent-soft)] t-accent' : 't-dim hover:text-[var(--text)]'}`}
            >
              <List className="h-4 w-4" />
            </button>
          </div>

          {/* Sort */}
          <div className="control-field flex items-center gap-2 rounded-lg px-3 py-2 text-[13px] font-medium t-dim">
            <ArrowUpDown className="h-3.5 w-3.5" />
            <span>{t('sort.label')}</span>
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value as 'name' | 'status')}
              className="cursor-pointer border-none bg-transparent text-[13px] font-semibold t-primary outline-none"
            >
              <option value="name" className="bg-[var(--surface-1)]">
                {t('sort.name')}
              </option>
              <option value="status" className="bg-[var(--surface-1)]">
                {t('sort.status')}
              </option>
            </select>
          </div>
        </div>
      </div>

      {/* Category filter pills */}
      <div className="-mx-2 flex items-center gap-1.5 overflow-x-auto px-2 scrollbar-none">
        <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg border brd t-faint">
          <Filter className="h-3.5 w-3.5" />
        </span>
        {categories.map((cat) => (
          <button
            key={cat}
            type="button"
            onClick={() => setSelectedCategory(cat)}
            className={`whitespace-nowrap rounded-lg border px-2.5 py-1 text-[12px] font-medium transition ${
              selectedCategory === cat
                ? 'border-[var(--accent-border)] bg-[var(--accent-soft)] t-accent'
                : 'brd t-dim hover:text-[var(--text)] hover:bg-[var(--surface-2)]'
            }`}
          >
            {cat === 'all' ? t('filter.all') : cat}
          </button>
        ))}
      </div>

      {/* Grid / grouped sections */}
      <div className="space-y-5 pt-1">
        {filteredAndSorted.length === 0 ? (
          <div className="glass p-12 text-center">
            <p className="text-[13px] t-dim">{t('empty.search', { query })}</p>
          </div>
        ) : isFlat ? (
          <motion.div variants={listVariants} initial="hidden" animate="show" className={GRID}>
            <AnimatePresence mode="popLayout">
              {appCards.map((card) => (
                <PluginCard key={card.name} card={card} onOpen={onOpen} canControl={!readOnly} />
              ))}
            </AnimatePresence>
          </motion.div>
        ) : (
          <div className="space-y-5">
            {grouped.map(([group, cards]) => (
              <section key={group} className="space-y-3">
                <div className="flex items-center gap-3">
                  <h3 className="text-[12px] font-semibold uppercase tracking-wide t-dim">
                    {group}
                  </h3>
                  <span className="rounded-md border brd bg-[var(--surface-inset)] px-1.5 py-0.5 text-[11px] font-semibold tabular-nums t-faint">
                    {cards.length}
                  </span>
                  <div className="h-px flex-1 bg-[var(--border)]" />
                </div>
                <motion.div
                  variants={listVariants}
                  initial="hidden"
                  animate="show"
                  className={GRID}
                >
                  {cards.map((card) => (
                    <PluginCard
                      key={card.name}
                      card={card}
                      onOpen={onOpen}
                      canControl={!readOnly}
                    />
                  ))}
                </motion.div>
              </section>
            ))}
          </div>
        )}

        {/* Secondary, collapsed bucket for framework/system plugins */}
        <SystemSection cards={systemCards} onOpen={onOpen} canControl={!readOnly} />
      </div>
    </motion.div>
  );
}
