import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { motion } from 'motion/react';
import { ArrowLeft, Lightbulb, Link2, List } from 'lucide-react';
import { useBrain } from '@/store';
import { api } from '@/lib/api';
import type { BacklinkContext, GraphData, LinkSuggestion } from '@/lib/types';
import { cn } from '@/lib/cn';
import { itemVariants, listVariants } from '@/lib/motion';
import { GraphView } from './graph/GraphView';
import { Outline } from './Outline';

/** Docked context panel: outline, local graph, backlinks-with-context, suggestions. */
export function RightRail() {
  const { t } = useTranslation();
  const active = useBrain((s) => s.active);
  const openNote = useBrain((s) => s.openNote);
  const openWiki = useBrain((s) => s.openWiki);
  const [hood, setHood] = useState<GraphData>({ nodes: [], edges: [] });
  const [backlinks, setBacklinks] = useState<BacklinkContext[]>([]);
  const [suggestions, setSuggestions] = useState<LinkSuggestion[]>([]);

  const id = active?.id;
  useEffect(() => {
    if (!id) return;
    api
      .neighborhood(id, 1)
      .then(setHood)
      .catch(() => setHood({ nodes: [], edges: [] }));
    api
      .backlinks(id)
      .then(setBacklinks)
      .catch(() => setBacklinks([]));
    api
      .suggestions(id, 6)
      .then(setSuggestions)
      .catch(() => setSuggestions([]));
  }, [id, active?.updated]);

  if (!active) return null;

  return (
    <motion.aside
      initial={{ opacity: 0, x: 12 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.18, ease: [0.22, 1, 0.36, 1] }}
      className="bb-glass hidden h-full w-72 shrink-0 flex-col gap-5 overflow-y-auto rounded-[var(--radius-lg)] p-4 lg:flex"
    >
      <Section title={t('rail.outline')} icon={<List className="size-3.5" />}>
        <Outline body={active.body} />
      </Section>

      <Section title={t('rail.localGraph')}>
        <div className="h-44 overflow-hidden rounded-lg border border-[var(--color-border)] bg-[var(--color-bg)]/50">
          <GraphView
            mode="2d"
            data={hood}
            activeId={id}
            width={240}
            height={176}
            onNode={(nid) => !nid.startsWith('tag:') && void openNote(nid)}
          />
        </div>
      </Section>

      <Section
        title={`${t('rail.backlinks')} (${backlinks.length})`}
        icon={<ArrowLeft className="size-3.5" />}
      >
        {backlinks.length ? (
          backlinks.map((b) => (
            <button
              key={b.id}
              onClick={() => void openNote(b.id)}
              className="block w-full rounded-lg px-2 py-1.5 text-left transition-colors hover:bg-[var(--color-elevated)]"
            >
              <span className="block truncate text-sm text-[var(--color-text)]">{b.title}</span>
              {b.snippet && (
                <span className="mt-0.5 block truncate text-xs text-[var(--color-faint)]">
                  {b.snippet}
                </span>
              )}
            </button>
          ))
        ) : (
          <Hint>{t('rail.noBacklinks')}</Hint>
        )}
      </Section>

      <Section
        title={t('rail.suggested')}
        icon={<Lightbulb className="size-3.5 text-[var(--color-accent)]" />}
      >
        {suggestions.length ? (
          suggestions.map((s) => (
            <RailRow
              key={`${s.id}-${s.reason}`}
              onClick={() => void openWiki(s.id, s.title)}
              label={s.title}
              badge={s.reason === 'unlinked-mention' ? t('rail.mention') : t('rail.similar')}
            />
          ))
        ) : (
          <Hint>{t('rail.noSuggestions')}</Hint>
        )}
      </Section>
    </motion.aside>
  );
}

function Section({
  title,
  icon,
  children,
}: {
  title: string;
  icon?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <div>
      <h3 className="mb-2 flex items-center gap-1.5 text-[0.7rem] font-semibold uppercase tracking-wider text-[var(--color-faint)]">
        {icon}
        {title}
      </h3>
      <motion.div variants={listVariants} initial="hidden" animate="show" className="space-y-0.5">
        {children}
      </motion.div>
    </div>
  );
}

function RailRow({
  label,
  badge,
  onClick,
}: {
  label: string;
  badge?: string;
  onClick: () => void;
}) {
  return (
    <motion.button
      variants={itemVariants}
      onClick={onClick}
      className={cn(
        'flex w-full items-center gap-1.5 rounded-lg px-2 py-1.5 text-left text-sm',
        'text-[var(--color-muted)] hover:bg-[var(--color-elevated)] hover:text-[var(--color-text)]'
      )}
    >
      <Link2 className="size-3 shrink-0 opacity-60" />
      <span className="truncate">{label}</span>
      {badge && (
        <span className="ml-auto rounded-full bg-[var(--color-accent-soft)] px-1.5 py-0.5 text-[10px] text-[var(--color-link)]">
          {badge}
        </span>
      )}
    </motion.button>
  );
}

function Hint({ children }: { children: React.ReactNode }) {
  return <p className="px-2 py-1 text-xs text-[var(--color-faint)]">{children}</p>;
}
