import { useEffect, useMemo, useState } from 'react';
import * as Tabs from '@radix-ui/react-tabs';
import { useQuery } from '@tanstack/react-query';
import {
  ArrowDownToLine,
  ArrowUpFromLine,
  Columns3,
  Database,
  Eye,
  Link2,
  Loader2,
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
  schema: Extract<UnifiedSchema, { kind: 'graph' }>;
  labelId?: string;
  focusedProperty?: string;
}

export function GraphDetail({
  open,
  onClose,
  connectionId,
  schema,
  labelId,
  focusedProperty,
}: Props) {
  const label = useMemo(
    () => (labelId ? schema.labels.find((l) => l.id === labelId) : undefined),
    [schema, labelId],
  );
  const relsOut = useMemo(
    () => (labelId ? schema.relationships.filter((r) => r.source === labelId) : []),
    [schema, labelId],
  );
  const relsIn = useMemo(
    () => (labelId ? schema.relationships.filter((r) => r.target === labelId) : []),
    [schema, labelId],
  );

  const [tab, setTab] = useState<'props' | 'rels' | 'sample'>('props');
  const [propFilter, setPropFilter] = useState('');
  const [relFilter, setRelFilter] = useState('');
  useEffect(() => {
    setTab('props');
    setPropFilter('');
    setRelFilter('');
  }, [labelId]);

  const filteredProps = useMemo(() => {
    const q = propFilter.trim().toLowerCase();
    if (!q || !label) return label?.properties ?? [];
    return label.properties.filter(
      (p) => p.name.toLowerCase().includes(q) || p.types.some((t) => t.toLowerCase().includes(q)),
    );
  }, [label, propFilter]);

  const setHoveredEntities = useAppStore((s) => s.setHoveredEntities);
  useEffect(() => () => setHoveredEntities(null), [setHoveredEntities]);

  const relQ = relFilter.trim().toLowerCase();
  const relsOutEntries = relsOut.map((r) => ({
    from: '(this)',
    to: `[:${r.type}]→(:${r.target})`,
    entityIds: labelId ? [labelId, r.target] : [r.target],
  }));
  const relsInEntries = relsIn.map((r) => ({
    from: `(:${r.source})-[:${r.type}]`,
    to: '(this)',
    entityIds: labelId ? [r.source, labelId] : [r.source],
  }));
  const matchRel = (e: { from: string; to: string }) =>
    !relQ || e.from.toLowerCase().includes(relQ) || e.to.toLowerCase().includes(relQ);
  const relsOutFiltered = relsOutEntries.filter(matchRel);
  const relsInFiltered = relsInEntries.filter(matchRel);
  const handleRelHover = (ids: string[] | null) => setHoveredEntities(ids);

  const sample = useQuery({
    queryKey: ['sample', connectionId, labelId],
    queryFn: () => api.sample({ connectionId: connectionId!, tableId: labelId!, rowLimit: 20 }),
    enabled: open && !!connectionId && !!labelId && tab === 'sample',
    retry: false,
    staleTime: 30_000,
  });

  return (
    <DrawerShell
      open={open}
      onClose={onClose}
      title={
        <span className="flex items-center gap-2">
          <Database className="w-3.5 h-3.5 text-accent" />
          <span>:{label?.label ?? '—'}</span>
        </span>
      }
      subtitle={`${label?.properties.length ?? 0} properties · ${relsOut.length + relsIn.length} relationships`}
      onCopy={() => copyToClipboard(JSON.stringify(label, null, 2), 'Label JSON copied')}
    >
      <Tabs.Root
        value={tab}
        onValueChange={(v) => setTab(v as 'props' | 'rels' | 'sample')}
        className="flex-1 min-h-0 flex flex-col"
      >
        <Tabs.List
          className="flex border-b px-2 shrink-0"
          style={{ borderColor: 'rgb(var(--border-subtle))' }}
        >
          <DrawerTab
            value="props"
            active={tab === 'props'}
            icon={<Columns3 className="w-3.5 h-3.5" />}
          >
            Properties
          </DrawerTab>
          <DrawerTab value="rels" active={tab === 'rels'} icon={<Link2 className="w-3.5 h-3.5" />}>
            Relationships
          </DrawerTab>
          <DrawerTab
            value="sample"
            active={tab === 'sample'}
            icon={<Eye className="w-3.5 h-3.5" />}
          >
            Sample
          </DrawerTab>
        </Tabs.List>

        <Tabs.Content value="props" className="flex-1 min-h-0 overflow-auto p-3">
          {label && label.properties.length > 6 && (
            <FilterBar
              value={propFilter}
              onChange={setPropFilter}
              placeholder="Filter properties by name or type…"
              count={filteredProps.length}
              total={label.properties.length}
            />
          )}
          <div className="flex flex-col gap-1">
            {filteredProps.map((p) => {
              const isFocused = p.name === focusedProperty;
              return (
                <div
                  key={p.name}
                  className={cn(
                    'flex items-center justify-between px-3 py-2 rounded-md text-[12px] font-mono transition-colors',
                    isFocused ? 'ring-1 ring-accent/60' : 'hover:bg-surface-2',
                  )}
                  style={{
                    background: isFocused
                      ? 'rgb(var(--accent) / 0.1)'
                      : 'rgb(var(--surface-2) / 0.4)',
                  }}
                >
                  <span className="truncate">{p.name}</span>
                  <span className="text-[10px] uppercase text-text-dim">{p.types.join('|')}</span>
                </div>
              );
            })}
          </div>
        </Tabs.Content>

        <Tabs.Content value="rels" className="flex-1 min-h-0 overflow-auto p-3">
          {relsOutEntries.length + relsInEntries.length > 4 && (
            <FilterBar
              value={relFilter}
              onChange={setRelFilter}
              placeholder="Filter relationships…"
              count={relsOutFiltered.length + relsInFiltered.length}
              total={relsOutEntries.length + relsInEntries.length}
            />
          )}
          <RelationsBlock
            title="Outgoing"
            icon={<ArrowUpFromLine className="w-3 h-3" />}
            edges={relsOutFiltered}
            onHover={handleRelHover}
          />
          <RelationsBlock
            title="Incoming"
            icon={<ArrowDownToLine className="w-3 h-3" />}
            edges={relsInFiltered}
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
