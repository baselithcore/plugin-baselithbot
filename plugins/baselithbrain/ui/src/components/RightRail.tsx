import { useEffect, useState } from 'react';
import { motion } from 'motion/react';
import { ArrowLeft, Sparkles, Link2 } from 'lucide-react';
import { useBrain } from '@/store';
import { api } from '@/lib/api';
import type { GraphData, LinkSuggestion, NoteMeta } from '@/lib/types';
import { cn } from '@/lib/cn';
import { itemVariants, listVariants } from '@/lib/motion';
import { GraphView } from './graph/GraphView';

/** Docked context panel: local graph + backlinks + link suggestions. */
export function RightRail() {
  const active = useBrain((s) => s.active);
  const notes = useBrain((s) => s.notes);
  const openNote = useBrain((s) => s.openNote);
  const openWiki = useBrain((s) => s.openWiki);
  const [hood, setHood] = useState<GraphData>({ nodes: [], edges: [] });
  const [suggestions, setSuggestions] = useState<LinkSuggestion[]>([]);

  const id = active?.id;
  useEffect(() => {
    if (!id) return;
    api
      .neighborhood(id, 1)
      .then(setHood)
      .catch(() => setHood({ nodes: [], edges: [] }));
    api
      .suggestions(id, 6)
      .then(setSuggestions)
      .catch(() => setSuggestions([]));
  }, [id, active?.updated]);

  if (!active) return null;
  const byId = (nid: string): NoteMeta | undefined => notes.find((n) => n.id === nid);

  return (
    <motion.aside
      initial={{ opacity: 0, x: 16 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.3, ease: [0.22, 1, 0.36, 1] }}
      className="bb-glass hidden h-full w-72 shrink-0 flex-col gap-5 overflow-y-auto rounded-[var(--radius-lg)] p-4 lg:flex"
    >
      <Section title="Local graph">
        <div className="bb-ring-grad h-44 overflow-hidden rounded-xl border border-[var(--color-border)] bg-[var(--color-bg)]/50">
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
        title={`Backlinks (${active.backlinks.length})`}
        icon={<ArrowLeft className="size-3.5" />}
      >
        {active.backlinks.length ? (
          active.backlinks.map((b) => (
            <RailRow key={b} onClick={() => void openNote(b)} label={byId(b)?.title || b} />
          ))
        ) : (
          <Hint>No notes link here yet.</Hint>
        )}
      </Section>

      <Section
        title="Suggested links"
        icon={<Sparkles className="size-3.5 text-[var(--color-accent)]" />}
      >
        {suggestions.length ? (
          suggestions.map((s) => (
            <RailRow
              key={`${s.id}-${s.reason}`}
              onClick={() => void openWiki(s.id, s.title)}
              label={s.title}
              badge={s.reason === 'unlinked-mention' ? 'mention' : 'similar'}
            />
          ))
        ) : (
          <Hint>No suggestions — well connected!</Hint>
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
      whileHover={{ x: 2 }}
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
