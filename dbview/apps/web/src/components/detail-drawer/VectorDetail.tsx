import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Database, Loader2 } from 'lucide-react';
import type { UnifiedSchema } from '@dbview/shared';
import { api } from '../../lib/api.js';
import { ResultTable } from '../ResultTable.js';
import { DrawerShell } from './DrawerShell.js';
import { copyToClipboard } from './shared.js';

interface Props {
  open: boolean;
  onClose: () => void;
  connectionId: string | null;
  schema: Extract<UnifiedSchema, { kind: 'vector' }>;
  collectionId?: string;
}

export function VectorDetail({ open, onClose, connectionId, schema, collectionId }: Props) {
  const collection = useMemo(
    () => (collectionId ? schema.collections.find((c) => c.id === collectionId) : undefined),
    [schema, collectionId],
  );

  const sample = useQuery({
    queryKey: ['qdrant-scroll', connectionId, collectionId],
    queryFn: () =>
      api.execute({
        connectionId: connectionId!,
        query: JSON.stringify({ op: 'scroll', collection: collection!.name, limit: 50 }),
        rowLimit: 50,
      }),
    enabled: open && !!connectionId && !!collection,
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
          <span>{collection?.name ?? '—'}</span>
          <span className="chip text-[9px] uppercase">qdrant</span>
        </span>
      }
      subtitle={`${collection?.payloadFields.length ?? 0} payload fields · ${
        collection?.vectorSize ?? 0
      }d ${collection?.distance ?? ''}${
        typeof collection?.pointCount === 'number' ? ` · ${collection.pointCount} pts` : ''
      }`}
      onCopy={() => copyToClipboard(JSON.stringify(collection, null, 2), 'Collection JSON copied')}
    >
      <div className="p-3 overflow-auto flex flex-col gap-3">
        <div>
          <div className="text-[10px] uppercase tracking-wider text-text-dim mb-2">
            Payload schema
          </div>
          <div className="flex flex-col gap-1">
            {collection?.payloadFields.map((p) => (
              <div
                key={p.name}
                className="flex items-center justify-between px-3 py-2 rounded-md text-[12px] font-mono"
                style={{ background: 'rgb(var(--surface-2) / 0.4)' }}
              >
                <span className="truncate">{p.name}</span>
                <div className="flex items-center gap-2 shrink-0">
                  <span className="text-[10px] uppercase text-text-dim">{p.types.join('|')}</span>
                  {p.sampleValues && p.sampleValues.length > 0 && (
                    <span
                      className="chip text-[9px] truncate max-w-[180px]"
                      title={p.sampleValues.join(', ')}
                    >
                      {p.sampleValues.slice(0, 2).join(', ')}
                      {p.sampleValues.length > 2 ? '…' : ''}
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
        <div>
          <div className="text-[10px] uppercase tracking-wider text-text-dim mb-2">
            Sample points
          </div>
          {sample.isLoading && (
            <div className="flex items-center justify-center p-6 text-text-muted text-[12px] gap-2">
              <Loader2 className="w-4 h-4 animate-spin" />
              loading sample…
            </div>
          )}
          {sample.error && (
            <div className="p-4 text-[12px] text-danger">{(sample.error as Error).message}</div>
          )}
          {sample.data && (
            <div
              className="h-[360px] flex flex-col rounded-md border"
              style={{ borderColor: 'rgb(var(--border-subtle))' }}
            >
              <ResultTable result={sample.data} embedded searchable />
            </div>
          )}
        </div>
      </div>
    </DrawerShell>
  );
}
