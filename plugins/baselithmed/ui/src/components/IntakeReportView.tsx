/**
 * Minimal renderer for the deterministic intake-report markdown shipped by
 * the backend (`### heading`, `- bullet`, `**bold**`, `_italic_`, `\`code\``).
 *
 * Avoids adding a markdown dependency for a single, controlled format. The
 * backend renderer (`flows/intake_report.py`) is the only writer, so the
 * parser only needs to handle that subset.
 */

import { useMemo } from 'react';
import { FileText } from 'lucide-react';

interface Props {
  markdown: string;
}

type Block =
  | { kind: 'heading'; text: string }
  | { kind: 'bullet'; items: string[] }
  | { kind: 'paragraph'; text: string };

export function IntakeReportView({ markdown }: Props) {
  const blocks = useMemo(() => parseBlocks(markdown), [markdown]);
  return (
    <section
      aria-label="Intake report"
      className="surface rounded-xl border border-ink-200/70 bg-white/70 p-4 text-sm leading-relaxed text-ink-700 shadow-e1 dark:border-ink-700/60 dark:bg-surface-dark-raised/70 dark:text-ink-100"
    >
      <header className="mb-3 flex items-center gap-2">
        <FileText className="h-3.5 w-3.5 text-ink-400 dark:text-ink-300" aria-hidden />
        <h3 className="text-2xs font-semibold uppercase tracking-[0.14em] text-ink-500 dark:text-ink-200">
          Pre-triage intake
        </h3>
      </header>
      <div className="space-y-2.5">
        {blocks.map((b, i) => (
          <BlockNode key={i} block={b} />
        ))}
      </div>
    </section>
  );
}

function BlockNode({ block }: { block: Block }) {
  if (block.kind === 'heading') {
    return (
      <h4 className="font-display text-xs font-semibold uppercase tracking-[0.1em] text-ink-800 dark:text-ink-50">
        {renderInline(block.text)}
      </h4>
    );
  }
  if (block.kind === 'bullet') {
    return (
      <ul className="ml-4 list-disc space-y-1">
        {block.items.map((it, i) => (
          <li key={i} className="text-xs leading-relaxed">
            {renderInline(it)}
          </li>
        ))}
      </ul>
    );
  }
  return <p className="text-xs leading-relaxed">{renderInline(block.text)}</p>;
}

function parseBlocks(md: string): Block[] {
  const lines = md.split('\n');
  const blocks: Block[] = [];
  let bullets: string[] | null = null;

  const flushBullets = () => {
    if (bullets) {
      blocks.push({ kind: 'bullet', items: bullets });
      bullets = null;
    }
  };

  for (const raw of lines) {
    const line = raw.trimEnd();
    if (!line.trim()) {
      flushBullets();
      continue;
    }
    if (line.startsWith('### ')) {
      flushBullets();
      blocks.push({ kind: 'heading', text: line.slice(4) });
      continue;
    }
    if (line.startsWith('- ')) {
      const item = line.slice(2);
      if (bullets === null) bullets = [];
      bullets.push(item);
      continue;
    }
    flushBullets();
    blocks.push({ kind: 'paragraph', text: line });
  }
  flushBullets();
  return blocks;
}

function renderInline(text: string): React.ReactNode {
  // Tokenizer order: `code`, **bold**, _italic_.
  const re = /(`[^`]+`|\*\*[^*]+\*\*|_[^_]+_)/g;
  const matches = Array.from(text.matchAll(re));
  if (matches.length === 0) return text;

  const out: React.ReactNode[] = [];
  let cursor = 0;
  let key = 0;
  for (const m of matches) {
    const idx = m.index ?? 0;
    if (idx > cursor) {
      out.push(text.slice(cursor, idx));
    }
    const tok = m[0];
    if (tok.startsWith('`')) {
      out.push(
        <code
          key={key++}
          className="rounded bg-ink-100 px-1 font-mono text-[10px] text-ink-700 dark:bg-ink-700/60 dark:text-ink-100"
        >
          {tok.slice(1, -1)}
        </code>
      );
    } else if (tok.startsWith('**')) {
      out.push(
        <strong key={key++} className="font-semibold text-ink-800 dark:text-ink-50">
          {tok.slice(2, -2)}
        </strong>
      );
    } else if (tok.startsWith('_')) {
      out.push(
        <em key={key++} className="italic text-ink-500 dark:text-ink-200">
          {tok.slice(1, -1)}
        </em>
      );
    }
    cursor = idx + tok.length;
  }
  if (cursor < text.length) out.push(text.slice(cursor));
  return <>{out}</>;
}
