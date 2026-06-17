import { useState } from 'react';
import { motion } from 'motion/react';
import { Check, Copy, FileText, Link2, ShieldCheck, Telescope } from 'lucide-react';
import { Markdown } from '../Markdown';
import type { Groundedness, ResearchTraceStep } from '@/lib/types';
import type { Msg } from './types';

/** One chat turn — user bubble, or assistant card with citations + actions. */
export function Bubble({
  msg,
  streaming,
  onOpen,
  onWiki,
}: {
  msg: Msg;
  streaming: boolean;
  onOpen: (id: string) => void;
  onWiki: (t: string) => void;
}) {
  if (msg.role === 'user') {
    return (
      <motion.div
        initial={{ opacity: 0, y: 8, scale: 0.98 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        transition={{ type: 'spring', stiffness: 400, damping: 28 }}
        className="flex justify-end"
      >
        <div className="bb-gradient max-w-[85%] whitespace-pre-wrap break-words rounded-2xl rounded-br-md px-3.5 py-2 text-sm text-white shadow-[0_6px_18px_-8px_hsl(258_88%_60%_/_0.6)]">
          {msg.text}
        </div>
      </motion.div>
    );
  }

  const empty = !msg.text;
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ type: 'spring', stiffness: 380, damping: 30 }}
      className="group rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)]/70 px-3.5 py-3 backdrop-blur-sm"
    >
      {empty && streaming ? (
        <div className="flex items-center py-1">
          <span className="bb-dot" />
          <span className="bb-dot" />
          <span className="bb-dot" />
        </div>
      ) : (
        <Markdown
          citations={Object.fromEntries((msg.sources ?? []).map((s) => [s.n, s]))}
          onCite={onOpen}
        >
          {msg.text}
        </Markdown>
      )}

      {msg.sources?.length ? (
        <div className="mt-2.5 flex flex-wrap gap-1 border-t border-[var(--color-border)] pt-2.5">
          {msg.sources.map((s) => (
            <button
              key={s.id}
              onClick={() => onOpen(s.id)}
              className="flex items-center gap-1 rounded-full bg-[var(--color-accent-soft)] px-2 py-0.5 text-[11px] text-[var(--color-link)] transition hover:brightness-110"
            >
              <FileText className="size-3" />[{s.n}] {s.title}
            </button>
          ))}
        </div>
      ) : null}

      {msg.suggestions?.length ? (
        <div className="mt-2 flex flex-wrap gap-1">
          {msg.suggestions.map((s) => (
            <button
              key={s}
              onClick={() => onWiki(s)}
              className="flex items-center gap-1 rounded-full border border-[var(--color-border)] px-2 py-0.5 text-[11px] text-[var(--color-muted)] transition hover:border-[var(--color-accent)] hover:text-[var(--color-text)]"
            >
              <Link2 className="size-3" />
              {s}
            </button>
          ))}
        </div>
      ) : null}

      {msg.trace?.length ? <TraceDisclosure trace={msg.trace} /> : null}

      <div className="mt-2 flex items-center gap-2">
        {!empty && <CopyButton text={msg.text} />}
        {msg.grounding ? <GroundingBadge g={msg.grounding} /> : null}
      </div>
    </motion.div>
  );
}

/** Collapsible Thought/Action/Observation log from a deep-research run. */
function TraceDisclosure({ trace }: { trace: ResearchTraceStep[] }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="mt-2.5 border-t border-[var(--color-border)] pt-2">
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex items-center gap-1 text-[11px] text-[var(--color-muted)] transition hover:text-[var(--color-accent)]"
      >
        <Telescope className="size-3" />
        {open ? 'Hide' : 'Show'} reasoning ({trace.length} steps)
      </button>
      {open ? (
        <ol className="mt-1.5 space-y-1">
          {trace.map((s, i) => (
            <li key={i} className="text-[11px] leading-snug text-[var(--color-faint)]">
              <span className="font-medium text-[var(--color-muted)]">
                {s.tool ? `${s.type}·${s.tool}` : s.type}:
              </span>{' '}
              {s.content.slice(0, 200)}
            </li>
          ))}
        </ol>
      ) : null}
    </div>
  );
}

/** Tints a faithfulness score: ≥0.75 green, ≥0.5 amber, else red. */
function GroundingBadge({ g }: { g: Groundedness }) {
  const pct = Math.round(g.score * 100);
  const tone =
    g.score >= 0.75 ? 'text-emerald-500' : g.score >= 0.5 ? 'text-amber-500' : 'text-rose-500';
  return (
    <span
      title={`Grounded in your notes — ${g.level}. ${g.feedback}`}
      className={`flex items-center gap-1 text-[11px] ${tone}`}
    >
      <ShieldCheck className="size-3" />
      {pct}% grounded
    </span>
  );
}

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <button
      onClick={() => {
        void navigator.clipboard.writeText(text);
        setCopied(true);
        setTimeout(() => setCopied(false), 1500);
      }}
      title="Copy"
      className="flex items-center gap-1 text-[11px] text-[var(--color-faint)] opacity-0 transition hover:text-[var(--color-accent)] group-hover:opacity-100"
    >
      {copied ? <Check className="size-3" /> : <Copy className="size-3" />}
      {copied ? 'Copied' : 'Copy'}
    </button>
  );
}
