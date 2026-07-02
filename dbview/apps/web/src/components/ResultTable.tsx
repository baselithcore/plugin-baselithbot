import { useMemo, useRef, useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { ArrowDown, ArrowUp, ArrowUpDown, Clock, Download, Hash, Search, X } from 'lucide-react';
import { useVirtualizer } from '@tanstack/react-virtual';
import type { ExecuteQueryResponse } from '@dbview/shared';
import { toast } from 'sonner';
import { cn } from '../lib/cn.js';
import { useDebouncedValue } from '../lib/use-debounced-value.js';

const VIRTUALIZE_THRESHOLD = 200;
const ROW_ESTIMATE_PX = 33;
const FILTER_DEBOUNCE_MS = 150;

interface Props {
  result: ExecuteQueryResponse;
  embedded?: boolean;
  /** Render an inline toolbar with row search + CSV export. Requires a flex-col parent with bounded height. */
  searchable?: boolean;
}

type SortDir = 'asc' | 'desc' | null;

export function ResultTable({ result, embedded = false, searchable = false }: Props) {
  const [sort, setSort] = useState<{ col: number; dir: SortDir } | null>(null);
  const [query, setQuery] = useState('');
  // Only stagger rows when this exact result first lands. Sort/scroll changes don't re-stagger.
  const seenResultRef = useRef<ExecuteQueryResponse | null>(null);
  const isFirstReveal = seenResultRef.current !== result;
  if (isFirstReveal) seenResultRef.current = result;

  // Defer the actual filter walk by 150ms — the input stays controlled and
  // snappy while big result sets (10k+ rows × 10+ columns) avoid filtering on
  // every keystroke.
  const debouncedQuery = useDebouncedValue(query, FILTER_DEBOUNCE_MS);
  const filtered = useMemo(() => {
    const q = debouncedQuery.trim().toLowerCase();
    if (!q) return result.rows;
    return result.rows.filter((r) => r.some((v) => cellSearchText(v).includes(q)));
  }, [result.rows, debouncedQuery]);

  const rows = useMemo(() => {
    if (!sort || sort.dir === null) return filtered;
    const copy = [...filtered];
    copy.sort((a, b) => {
      const av = a[sort.col];
      const bv = b[sort.col];
      const an = numericish(av);
      const bn = numericish(bv);
      let cmp: number;
      if (an !== null && bn !== null) cmp = an - bn;
      else cmp = String(av ?? '').localeCompare(String(bv ?? ''));
      return sort.dir === 'asc' ? cmp : -cmp;
    });
    return copy;
  }, [filtered, sort]);

  const toggleSort = (col: number) => {
    setSort((prev) => {
      if (!prev || prev.col !== col) return { col, dir: 'asc' };
      if (prev.dir === 'asc') return { col, dir: 'desc' };
      return null;
    });
  };

  const exportCsv = () => {
    const header = result.columns.join(',');
    const lines = result.rows.map((r) => r.map((v) => csvCell(v)).join(','));
    const csv = [header, ...lines].join('\n');
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `dbview-${Date.now()}.csv`;
    a.click();
    URL.revokeObjectURL(url);
    toast.success('CSV downloaded');
  };

  const useFlexLayout = !embedded || searchable;
  const hiddenCount = result.rows.length - filtered.length;

  const scrollRef = useRef<HTMLDivElement>(null);
  const shouldVirtualize = useFlexLayout && rows.length > VIRTUALIZE_THRESHOLD;
  const virtualizer = useVirtualizer({
    count: rows.length,
    getScrollElement: () => scrollRef.current,
    estimateSize: () => ROW_ESTIMATE_PX,
    overscan: 10,
    enabled: shouldVirtualize,
  });
  const virtualItems = shouldVirtualize ? virtualizer.getVirtualItems() : [];
  const totalSize = shouldVirtualize ? virtualizer.getTotalSize() : 0;
  const paddingTop = virtualItems[0]?.start ?? 0;
  const paddingBottom = shouldVirtualize
    ? totalSize - (virtualItems[virtualItems.length - 1]?.end ?? 0)
    : 0;

  return (
    <div
      className={cn(
        embedded
          ? searchable
            ? 'flex flex-col h-full min-h-0'
            : 'contents'
          : 'panel flex flex-col h-full min-h-0'
      )}
    >
      {!embedded && (
        <div className="panel-header">
          <div className="flex items-center gap-2 text-[13px] font-semibold">
            <span>Results</span>
            <span className="metric-chip h-6">
              <Hash className="w-3 h-3" />
              {result.rowCount}
            </span>
            <span className="metric-chip h-6">
              <Clock className="w-3 h-3" />
              {result.durationMs}ms
            </span>
            {result.truncated && <span className="chip chip-warn">truncated</span>}
          </div>
          <button onClick={exportCsv} className="btn-ghost" title="Export CSV">
            <Download className="w-3.5 h-3.5" />
          </button>
        </div>
      )}
      {searchable && (
        <div
          className="flex items-center gap-2 px-3 h-9 border-b shrink-0"
          style={{ borderColor: 'rgb(var(--border-subtle))' }}
        >
          <Search className="w-3.5 h-3.5 text-text-dim shrink-0" />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Escape' && query) {
                e.stopPropagation();
                setQuery('');
              }
            }}
            placeholder="Filter rows…"
            aria-label="Filter rows"
            className="bg-transparent flex-1 outline-none text-[12px] placeholder:text-text-dim"
          />
          <span className="text-[10px] font-mono text-text-dim shrink-0">
            {query ? `${filtered.length}/${result.rows.length}` : `${result.rows.length} rows`}
          </span>
          {query && (
            <button
              onClick={() => setQuery('')}
              className="btn-icon w-5 h-5"
              aria-label="Clear filter"
              title="Clear (Esc)"
            >
              <X className="w-3 h-3" />
            </button>
          )}
          <button
            onClick={exportCsv}
            className="btn-icon w-6 h-6 shrink-0"
            aria-label="Export CSV"
            title="Export CSV"
          >
            <Download className="w-3.5 h-3.5" />
          </button>
        </div>
      )}
      <div ref={scrollRef} className={cn(useFlexLayout ? 'flex-1 min-h-0 overflow-auto' : 'block')}>
        <table className="text-[12px] font-mono w-full border-collapse">
          <thead
            className="sticky top-0 z-10"
            style={{
              background: 'linear-gradient(180deg, rgb(var(--surface-2)), rgb(var(--surface-1)))',
            }}
          >
            <tr>
              {result.columns.map((c, i) => {
                const isSorted = sort?.col === i;
                return (
                  <th
                    key={c}
                    onClick={() => toggleSort(i)}
                    className={cn(
                      'text-left px-3 py-2.5 font-semibold cursor-pointer select-none border-b group whitespace-nowrap',
                      isSorted ? 'text-accent' : 'text-text-muted hover:text-text'
                    )}
                    style={{ borderColor: 'rgb(var(--border-subtle))' }}
                  >
                    <span className="inline-flex items-center gap-1.5">
                      {c}
                      <AnimatePresence initial={false} mode="wait">
                        {isSorted ? (
                          <motion.span
                            key={sort?.dir ?? 'none'}
                            initial={{ opacity: 0, rotate: sort?.dir === 'asc' ? 180 : -180 }}
                            animate={{ opacity: 1, rotate: 0 }}
                            exit={{ opacity: 0 }}
                            transition={{ duration: 0.18, ease: [0.22, 1, 0.36, 1] }}
                            className="inline-flex"
                          >
                            {sort?.dir === 'asc' ? (
                              <ArrowUp className="w-3 h-3" />
                            ) : (
                              <ArrowDown className="w-3 h-3" />
                            )}
                          </motion.span>
                        ) : (
                          <ArrowUpDown
                            key="idle"
                            className="w-3 h-3 opacity-0 group-hover:opacity-50"
                          />
                        )}
                      </AnimatePresence>
                    </span>
                  </th>
                );
              })}
            </tr>
          </thead>
          <tbody>
            {paddingTop > 0 && (
              <tr aria-hidden style={{ height: paddingTop }}>
                <td colSpan={result.columns.length} />
              </tr>
            )}
            {(shouldVirtualize
              ? virtualItems
                  .map((vi) => ({ row: rows[vi.index], i: vi.index }))
                  .filter(
                    (x): x is { row: (typeof rows)[number]; i: number } => x.row !== undefined
                  )
              : rows.map((row, i) => ({ row, i }))
            ).map(({ row, i }) => {
              const stagger = !shouldVirtualize && isFirstReveal && i < 24;
              const cells = row.map((v, j) => (
                <td key={j} className="px-3 py-2 text-text max-w-[320px] truncate">
                  {formatCell(v)}
                </td>
              ));
              if (stagger) {
                return (
                  <motion.tr
                    key={i}
                    initial={{ opacity: 0, y: 4 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.24, ease: [0.22, 1, 0.36, 1], delay: i * 0.014 }}
                    className="hover:bg-surface-2/70 transition-colors"
                    style={{ borderBottom: '1px solid rgb(var(--border-subtle) / 0.54)' }}
                  >
                    {cells}
                  </motion.tr>
                );
              }
              return (
                <tr
                  key={i}
                  className="hover:bg-surface-2/70 transition-colors"
                  style={{ borderBottom: '1px solid rgb(var(--border-subtle) / 0.54)' }}
                >
                  {cells}
                </tr>
              );
            })}
            {paddingBottom > 0 && (
              <tr aria-hidden style={{ height: paddingBottom }}>
                <td colSpan={result.columns.length} />
              </tr>
            )}
            {rows.length === 0 && (
              <tr>
                <td colSpan={result.columns.length} className="text-center py-8 text-text-dim">
                  {hiddenCount > 0 && query ? `No rows match "${query}".` : 'No rows returned.'}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function formatCell(v: unknown) {
  if (v === null || v === undefined) return <span className="text-text-dim italic">null</span>;
  if (typeof v === 'boolean')
    return <span className={v ? 'text-success' : 'text-danger'}>{String(v)}</span>;
  if (typeof v === 'number') return <span className="text-amber-400">{v}</span>;
  if (typeof v === 'object') return <span className="text-violet-400">{JSON.stringify(v)}</span>;
  return String(v);
}

function csvCell(v: unknown): string {
  if (v === null || v === undefined) return '';
  const s = typeof v === 'object' ? JSON.stringify(v) : String(v);
  return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
}

function cellSearchText(v: unknown): string {
  if (v === null || v === undefined) return '';
  if (typeof v === 'object') return JSON.stringify(v).toLowerCase();
  return String(v).toLowerCase();
}

function numericish(v: unknown): number | null {
  if (typeof v === 'number') return v;
  if (typeof v === 'string') {
    const n = Number(v);
    return Number.isFinite(n) ? n : null;
  }
  return null;
}
