import { Quote } from 'lucide-react';
import { cn } from '../../lib/cn';
import type { Verbatim } from '../../lib/verbatim';

export function VerbatimList({
  items,
  focused,
}: {
  items: Verbatim[];
  focused: Verbatim | null;
}) {
  return (
    <div className="px-4 py-3 space-y-2">
      <div className="flex items-center gap-1.5 text-[10px] font-semibold uppercase text-ink-subtle">
        <Quote size={11} aria-hidden />
        Verbatim
        <span className="tabular-nums">({items.length})</span>
      </div>
      {items.map((v, i) => (
        <div
          key={i}
          data-kind={v.kind}
          className={cn('verbatim-card', focused === v && 'ring-2 ring-[var(--color-brand-ring)]')}
        >
          <div className="verbatim-header">
            [{v.kind}] {v.header}
          </div>
          <div className="verbatim-body">{v.body || '—'}</div>
        </div>
      ))}
    </div>
  );
}
