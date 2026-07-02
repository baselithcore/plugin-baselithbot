import { useEffect, useMemo, useState } from 'react';
import * as Tabs from '@radix-ui/react-tabs';
import { useQuery } from '@tanstack/react-query';
import {
  ArrowDownToLine,
  ArrowUpFromLine,
  Columns3,
  Eye,
  Key,
  Link2,
  Loader2,
  Table as TableIcon,
} from 'lucide-react';
import type { UnifiedSchema } from '@dbview/shared';
import { api } from '../../lib/api.js';
import { cn } from '../../lib/cn.js';
import { useAppStore } from '../../store/app.js';
import { ResultTable } from '../ResultTable.js';
import { DrawerShell, DrawerTab } from './DrawerShell.js';
import { FilterBar, RelationsBlock, copyToClipboard } from './shared.js';

interface Props {
  open: boolean;
  onClose: () => void;
  connectionId: string | null;
  schema: Extract<UnifiedSchema, { kind: 'relational' }>;
  tableId?: string;
  focusedColumn?: string;
}

export function RelationalDetail({
  open,
  onClose,
  connectionId,
  schema,
  tableId,
  focusedColumn,
}: Props) {
  const table = useMemo(
    () => (tableId ? schema.tables.find((t) => t.id === tableId) : undefined),
    [schema, tableId]
  );
  const fkOut = useMemo(
    () => (tableId ? schema.edges.filter((e) => e.source === tableId) : []),
    [schema, tableId]
  );
  const fkIn = useMemo(
    () => (tableId ? schema.edges.filter((e) => e.target === tableId) : []),
    [schema, tableId]
  );

  const [tab, setTab] = useState<'columns' | 'relations' | 'sample'>('columns');
  const [colFilter, setColFilter] = useState('');
  const [relFilter, setRelFilter] = useState('');
  useEffect(() => {
    setTab('columns');
    setColFilter('');
    setRelFilter('');
  }, [tableId]);

  const filteredColumns = useMemo(() => {
    const q = colFilter.trim().toLowerCase();
    if (!q || !table) return table?.columns ?? [];
    return table.columns.filter(
      (c) => c.name.toLowerCase().includes(q) || c.dataType.toLowerCase().includes(q)
    );
  }, [table, colFilter]);

  const setHoveredEntities = useAppStore((s) => s.setHoveredEntities);
  useEffect(() => () => setHoveredEntities(null), [setHoveredEntities]);

  const relFilterQ = relFilter.trim().toLowerCase();
  const fkOutEntries = fkOut.map((e) => ({
    from: e.sourceColumn,
    to: `${e.target}.${e.targetColumn}`,
    constraint: e.constraintName,
    entityIds: tableId ? [tableId, e.target] : [e.target],
  }));
  const fkInEntries = fkIn.map((e) => ({
    from: `${e.source}.${e.sourceColumn}`,
    to: e.targetColumn,
    constraint: e.constraintName,
    entityIds: tableId ? [e.source, tableId] : [e.source],
  }));
  const matchRel = (e: { from: string; to: string; constraint?: string }) =>
    !relFilterQ ||
    e.from.toLowerCase().includes(relFilterQ) ||
    e.to.toLowerCase().includes(relFilterQ) ||
    (e.constraint?.toLowerCase().includes(relFilterQ) ?? false);
  const fkOutFiltered = fkOutEntries.filter(matchRel);
  const fkInFiltered = fkInEntries.filter(matchRel);
  const handleRelHover = (ids: string[] | null) => setHoveredEntities(ids);

  const sample = useQuery({
    queryKey: ['sample', connectionId, tableId],
    queryFn: () => api.sample({ connectionId: connectionId!, tableId: tableId!, rowLimit: 20 }),
    enabled: open && !!connectionId && !!tableId && tab === 'sample',
    retry: false,
    staleTime: 30_000,
  });

  return (
    <DrawerShell
      open={open}
      onClose={onClose}
      title={
        <span className="flex items-center gap-2">
          <TableIcon className="w-3.5 h-3.5 text-accent" />
          <span>{table?.name ?? '—'}</span>
          <span className="chip text-[9px] uppercase">{table?.schema}</span>
        </span>
      }
      subtitle={`${table?.columns.length ?? 0} columns · ${fkOut.length + fkIn.length} relations`}
      onCopy={() => copyToClipboard(JSON.stringify(table, null, 2), 'Table JSON copied')}
    >
      <Tabs.Root
        value={tab}
        onValueChange={(v) => setTab(v as 'columns' | 'relations' | 'sample')}
        className="flex-1 min-h-0 flex flex-col"
      >
        <Tabs.List
          className="flex border-b px-2 shrink-0"
          style={{ borderColor: 'rgb(var(--border-subtle))' }}
        >
          <DrawerTab
            value="columns"
            active={tab === 'columns'}
            icon={<Columns3 className="w-3.5 h-3.5" />}
          >
            Columns
          </DrawerTab>
          <DrawerTab
            value="relations"
            active={tab === 'relations'}
            icon={<Link2 className="w-3.5 h-3.5" />}
          >
            Relations
          </DrawerTab>
          <DrawerTab
            value="sample"
            active={tab === 'sample'}
            icon={<Eye className="w-3.5 h-3.5" />}
          >
            Sample data
          </DrawerTab>
        </Tabs.List>

        <Tabs.Content value="columns" className="flex-1 min-h-0 overflow-auto p-3">
          {table && table.columns.length > 6 && (
            <FilterBar
              value={colFilter}
              onChange={setColFilter}
              placeholder="Filter columns by name or type…"
              count={filteredColumns.length}
              total={table.columns.length}
            />
          )}
          <div className="flex flex-col gap-1">
            {filteredColumns.map((c) => {
              const isFocused = c.name === focusedColumn;
              return (
                <div
                  key={c.name}
                  className={cn(
                    'flex items-center justify-between px-3 py-2 rounded-md text-[12px] font-mono transition-colors',
                    isFocused ? 'ring-1 ring-accent/60' : 'hover:bg-surface-2'
                  )}
                  style={{
                    background: isFocused
                      ? 'rgb(var(--accent) / 0.1)'
                      : 'rgb(var(--surface-2) / 0.4)',
                  }}
                >
                  <div className="flex items-center gap-2 min-w-0">
                    {c.isPrimaryKey ? (
                      <Key className="w-3 h-3 text-amber-400 shrink-0" strokeWidth={2.5} />
                    ) : c.isForeignKey ? (
                      <Link2 className="w-3 h-3 text-sky-400 shrink-0" strokeWidth={2.5} />
                    ) : (
                      <span className="w-3 h-3 inline-block shrink-0" />
                    )}
                    <span className={cn('truncate', c.isPrimaryKey && 'font-semibold')}>
                      {c.name}
                    </span>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <span className="text-[10px] uppercase text-text-dim">{c.dataType}</span>
                    {!c.nullable && <span className="chip chip-danger text-[9px]">NOT NULL</span>}
                    {c.isUnique && <span className="chip text-[9px]">UNIQUE</span>}
                  </div>
                </div>
              );
            })}
          </div>
        </Tabs.Content>

        <Tabs.Content value="relations" className="flex-1 min-h-0 overflow-auto p-3">
          {fkOutEntries.length + fkInEntries.length > 4 && (
            <FilterBar
              value={relFilter}
              onChange={setRelFilter}
              placeholder="Filter relations…"
              count={fkOutFiltered.length + fkInFiltered.length}
              total={fkOutEntries.length + fkInEntries.length}
            />
          )}
          <RelationsBlock
            title="Outgoing"
            icon={<ArrowUpFromLine className="w-3 h-3" />}
            edges={fkOutFiltered}
            onHover={handleRelHover}
          />
          <RelationsBlock
            title="Incoming"
            icon={<ArrowDownToLine className="w-3 h-3" />}
            edges={fkInFiltered}
            onHover={handleRelHover}
          />
        </Tabs.Content>

        <Tabs.Content
          value="sample"
          className="flex-1 min-h-0 flex flex-col data-[state=inactive]:hidden"
        >
          {sample.isLoading && (
            <div className="flex items-center justify-center p-8 text-text-muted text-[12px] gap-2">
              <Loader2 className="w-4 h-4 animate-spin" />
              loading sample…
            </div>
          )}
          {sample.error && (
            <div className="p-4 text-[12px] text-danger">{(sample.error as Error).message}</div>
          )}
          {sample.data && (
            <div className="flex-1 min-h-0 flex flex-col">
              <ResultTable result={sample.data} embedded searchable />
            </div>
          )}
        </Tabs.Content>
      </Tabs.Root>
    </DrawerShell>
  );
}
