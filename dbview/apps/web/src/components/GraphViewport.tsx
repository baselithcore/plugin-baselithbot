import { lazy, Suspense, useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { ReactFlowProvider } from '@xyflow/react';
import { motion } from 'framer-motion';
import { Database, Network } from 'lucide-react';
import { dialectKind, type UnifiedSchema } from '@dbview/shared';
import { api } from '../lib/api.js';
import { useAppStore } from '../store/app.js';
import { SchemaGraphView } from '../graph/SchemaGraphView.js';
import { PropertyGraphView } from '../graph/PropertyGraphView.js';
import { GraphSkeleton } from './ui/Skeleton.js';
import { EmptyState } from './ui/EmptyState.js';
import { ResultTable } from './ResultTable.js';
import { Toolbar } from './graph-viewport/Toolbar.js';
import { Legend } from './graph-viewport/Legend.js';
import { ViewToggles } from './graph-viewport/ViewToggles.js';
import { VectorStoreView } from './graph-viewport/VectorStoreView.js';
import { KeyValueStoreView } from './graph-viewport/KeyValueStoreView.js';
import { SearchStoreView } from './graph-viewport/SearchStoreView.js';
import { DocumentStoreView } from './graph-viewport/DocumentStoreView.js';
import { DATA_PREVIEW_QUERY_KEY, useDataPreview } from './graph-viewport/use-data-preview.js';
import { useDebouncedValue } from '../lib/use-debounced-value.js';

const ResultGraph2DView = lazy(() =>
  import('../graph/ResultGraph2DView.js').then((m) => ({ default: m.ResultGraph2DView })),
);
const ResultGraph3DView = lazy(() =>
  import('../graph/ResultGraph3DView.js').then((m) => ({ default: m.ResultGraph3DView })),
);

export function GraphViewport() {
  const qc = useQueryClient();
  const connId = useAppStore((s) => s.activeConnectionId);
  const highlightedFromQuery = useAppStore((s) => s.highlightedTables);
  const hovered = useAppStore((s) => s.hoveredEntities);
  const highlighted = useMemo(() => {
    if (hovered.size === 0) return highlightedFromQuery;
    const merged = new Set(highlightedFromQuery);
    for (const id of hovered) merged.add(id);
    return merged;
  }, [highlightedFromQuery, hovered]);
  const search = useAppStore((s) => s.schemaSearch);
  const setSearch = useAppStore((s) => s.setSchemaSearch);
  // Heavy O(entities × fields) filter — defer until typing pauses so each
  // keystroke stays cheap even on connections with hundreds of tables.
  const debouncedSearch = useDebouncedValue(search, 220);
  const selectTable = useAppStore((s) => s.selectTable);
  const selectColumn = useAppStore((s) => s.selectColumn);
  const view3D = useAppStore((s) => s.graphView3D);
  const setView3D = useAppStore((s) => s.setGraphView3D);
  const dataMode = useAppStore((s) => s.graphDataMode);
  const setDataMode = useAppStore((s) => s.setGraphDataMode);
  const minimapVisible = useAppStore((s) => s.minimapVisible);
  const toggleMinimapVisible = useAppStore((s) => s.toggleMinimapVisible);
  const legendVisible = useAppStore((s) => s.legendVisible);
  const toggleLegendVisible = useAppStore((s) => s.toggleLegendVisible);
  // Bumped by Refresh; SchemaGraphView observes this and re-runs dagre,
  // discarding any user-applied drag positions for a clean tidy layout.
  const [layoutNonce, setLayoutNonce] = useState(0);

  // Browser-level fullscreen on the canvas panel. We track state via the
  // `fullscreenchange` event so the toolbar icon reflects user actions like
  // Esc-to-exit handled by the browser without going through our handler.
  const containerRef = useRef<HTMLDivElement>(null);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const canFullscreen =
    typeof document !== 'undefined' && typeof document.fullscreenEnabled === 'boolean'
      ? document.fullscreenEnabled
      : true;

  useEffect(() => {
    function onChange() {
      setIsFullscreen(document.fullscreenElement === containerRef.current);
    }
    document.addEventListener('fullscreenchange', onChange);
    return () => document.removeEventListener('fullscreenchange', onChange);
  }, []);

  const onToggleFullscreen = useCallback(async () => {
    const el = containerRef.current;
    if (!el) return;
    try {
      if (document.fullscreenElement === el) {
        await document.exitFullscreen();
      } else if (!document.fullscreenElement) {
        await el.requestFullscreen();
      } else {
        // Another element is fullscreen; swap to ours.
        await document.exitFullscreen();
        await el.requestFullscreen();
      }
    } catch {
      // User denied / unavailable. State stays in sync via `fullscreenchange`
      // — no toast needed; the icon does not flip.
    }
  }, []);

  const schema = useQuery({
    queryKey: ['schema', connId],
    queryFn: () => api.getSchema(connId!),
    enabled: !!connId,
  });

  const isGraphDialect = schema.data ? dialectKind(schema.data.dialect) === 'graph' : false;
  const isVectorDialect = schema.data ? dialectKind(schema.data.dialect) === 'vector' : false;
  const showDataPreview = (isGraphDialect || isVectorDialect) && dataMode === 'data';

  const { query: dataPreview, counts: dataPreviewCounts } = useDataPreview(
    connId,
    schema.data,
    showDataPreview,
  );

  const matched = useMemo<Set<string> | undefined>(() => {
    if (!schema.data || !debouncedSearch.trim()) return undefined;
    const q = debouncedSearch.toLowerCase();
    if (schema.data.kind === 'relational') {
      const ids = new Set<string>();
      for (const t of schema.data.tables) {
        if (
          t.name.toLowerCase().includes(q) ||
          t.id.toLowerCase().includes(q) ||
          t.columns.some((c) => c.name.toLowerCase().includes(q))
        ) {
          ids.add(t.id);
        }
      }
      return ids;
    }
    if (schema.data.kind === 'graph') {
      const ids = new Set<string>();
      for (const l of schema.data.labels) {
        if (
          l.label.toLowerCase().includes(q) ||
          l.id.toLowerCase().includes(q) ||
          l.properties.some((p) => p.name.toLowerCase().includes(q))
        ) {
          ids.add(l.id);
        }
      }
      for (const r of schema.data.relationships) {
        if (
          r.type.toLowerCase().includes(q) ||
          r.id.toLowerCase().includes(q) ||
          r.properties.some((p) => p.name.toLowerCase().includes(q))
        ) {
          ids.add(r.id);
        }
      }
      return ids;
    }
    if (schema.data.kind === 'vector') {
      const ids = new Set<string>();
      for (const c of schema.data.collections) {
        if (
          c.name.toLowerCase().includes(q) ||
          c.payloadFields.some((p) => p.name.toLowerCase().includes(q))
        ) {
          ids.add(c.id);
        }
      }
      return ids;
    }
    if (schema.data.kind === 'keyvalue') {
      const ids = new Set<string>();
      for (const n of schema.data.namespaces) {
        if (
          n.pattern.toLowerCase().includes(q) ||
          n.sampleKeys.some((k) => k.toLowerCase().includes(q))
        ) {
          ids.add(n.pattern);
        }
      }
      return ids;
    }
    if (schema.data.kind === 'search') {
      const ids = new Set<string>();
      for (const idx of schema.data.indices) {
        if (
          idx.name.toLowerCase().includes(q) ||
          idx.fields.some((f) => f.name.toLowerCase().includes(q))
        ) {
          ids.add(idx.id);
        }
      }
      return ids;
    }
    if (schema.data.kind === 'document') {
      const ids = new Set<string>();
      for (const c of schema.data.collections) {
        if (
          c.name.toLowerCase().includes(q) ||
          c.fields.some((f) => f.name.toLowerCase().includes(q))
        ) {
          ids.add(c.id);
        }
      }
      return ids;
    }
    return undefined;
  }, [schema.data, debouncedSearch]);

  if (!connId) {
    return (
      <div className="panel h-full overflow-hidden grid-bg">
        <EmptyState
          icon={<Database className="w-5 h-5" />}
          title="Pick a connection"
          description="Select a database from the left to visualize its schema as an interactive graph."
        />
      </div>
    );
  }

  if (schema.isLoading) {
    return (
      <div className="panel h-full overflow-hidden relative">
        <GraphSkeleton />
      </div>
    );
  }

  if (schema.error) {
    const e = schema.error as Error & { code?: string };
    const unreachable = e.code === 'connection_unreachable';
    return (
      <div className="panel h-full overflow-hidden">
        <EmptyState
          icon={<Network className="w-5 h-5 text-danger" />}
          title={unreachable ? 'Database unreachable' : 'Could not load schema'}
          description={e.message}
          action={
            <button
              className="btn"
              onClick={() => qc.invalidateQueries({ queryKey: ['schema', connId] })}
            >
              Retry
            </button>
          }
        />
      </div>
    );
  }

  const data = schema.data!;
  const counts =
    data.kind === 'relational'
      ? { primary: `${data.tables.length} tables`, secondary: `${data.edges.length} FK` }
      : data.kind === 'graph'
        ? showDataPreview && dataPreviewCounts
          ? {
              primary: `${dataPreviewCounts.nodes} nodes`,
              secondary: `${dataPreviewCounts.edges} rel`,
            }
          : {
              primary: `${data.labels.length} labels`,
              secondary: `${data.relationships.length} rel`,
            }
        : data.kind === 'vector'
          ? showDataPreview && dataPreview.data
            ? {
                primary: `${dataPreview.data.rowCount} points`,
                secondary: `${dataPreview.data.columns.length} fields`,
              }
            : {
                primary: `${data.collections.length} collections`,
                secondary: `${data.collections.reduce(
                  (acc: number, c) => acc + (c.pointCount ?? 0),
                  0,
                )} pts`,
              }
          : data.kind === 'keyvalue'
            ? {
                primary: `${data.namespaces.length} namespaces`,
                secondary: `${data.totalKeys.toLocaleString()} keys`,
              }
            : data.kind === 'search'
              ? {
                  primary: `${data.indices.length} indices`,
                  secondary: `${data.indices.reduce(
                    (acc: number, i) => acc + (i.docCount ?? 0),
                    0,
                  )} docs`,
                }
              : {
                  primary: `${data.collections.length} collections`,
                  secondary: `${data.collections.reduce(
                    (acc: number, c) => acc + (c.docCount ?? 0),
                    0,
                  )} docs`,
                };
  const matchCount = matched?.size ?? null;
  const totalSearchable = totalSearchableFor(data);
  // True while the user is still typing and the debounced filter has not yet
  // caught up — drives a subtle pulse on the magnifier so they know their
  // change is being processed.
  const searchPending = search !== debouncedSearch;
  const dataThreeD = data.kind === 'graph' && showDataPreview && view3D;

  return (
    <ReactFlowProvider>
      <motion.div
        ref={containerRef}
        data-tour="graph-viewport"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className="panel h-full overflow-hidden relative grid-bg"
      >
        {showDataPreview ? (
          dataPreview.isLoading ? (
            <GraphSkeleton />
          ) : dataPreview.error ? (
            <EmptyState
              icon={<Network className="w-5 h-5 text-danger" />}
              title="Could not load data preview"
              description={(dataPreview.error as Error).message}
              action={
                <button
                  className="btn"
                  onClick={() =>
                    qc.invalidateQueries({ queryKey: [DATA_PREVIEW_QUERY_KEY, connId] })
                  }
                >
                  Retry
                </button>
              }
            />
          ) : dataPreview.data && dataPreview.data.rows.length > 0 ? (
            data.kind === 'vector' ? (
              <div className="absolute inset-0 pt-16 px-3 pb-3 flex flex-col min-h-0">
                <ResultTable result={dataPreview.data} embedded />
              </div>
            ) : dataThreeD ? (
              <Suspense fallback={<GraphSkeleton />}>
                <ResultGraph3DView result={dataPreview.data} />
              </Suspense>
            ) : (
              <Suspense fallback={<GraphSkeleton />}>
                <ResultGraph2DView result={dataPreview.data} />
              </Suspense>
            )
          ) : (
            <EmptyState
              icon={<Database className="w-5 h-5" />}
              title="No data in graph"
              description="The graph is empty. Insert nodes/relationships from your client to see them here."
            />
          )
        ) : data.kind === 'relational' ? (
          <SchemaGraphView
            graph={data}
            highlightedTables={highlighted}
            matchedTables={matched}
            onSelectTable={selectTable}
            onSelectColumn={selectColumn}
            layoutNonce={layoutNonce}
          />
        ) : data.kind === 'graph' ? (
          <PropertyGraphView
            graph={data}
            highlightedLabels={highlighted}
            matchedLabels={matched}
            onSelectLabel={selectTable}
            onSelectProperty={selectColumn}
          />
        ) : data.kind === 'vector' ? (
          <VectorStoreView schema={data} matched={matched} onSelectCollection={selectTable} />
        ) : data.kind === 'keyvalue' ? (
          <KeyValueStoreView schema={data} matched={matched} onSelectNamespace={selectTable} />
        ) : data.kind === 'search' ? (
          <SearchStoreView schema={data} matched={matched} onSelectIndex={selectTable} />
        ) : (
          <DocumentStoreView schema={data} matched={matched} onSelectCollection={selectTable} />
        )}

        <Toolbar
          countsPrimary={counts.primary}
          countsSecondary={counts.secondary}
          search={search}
          setSearch={setSearch}
          searchPlaceholder={searchPlaceholderFor(data.kind)}
          matchCount={matchCount}
          totalSearchable={totalSearchable}
          searchPending={searchPending}
          isFetching={schema.isFetching || dataPreview.isFetching}
          onRefresh={() => {
            qc.invalidateQueries({ queryKey: ['schema', connId] });
            if (showDataPreview) {
              qc.invalidateQueries({ queryKey: [DATA_PREVIEW_QUERY_KEY, connId] });
            }
            // Force a clean re-layout regardless of whether the schema bytes
            // changed — user clicked Refresh expecting a tidy view.
            setLayoutNonce((n) => n + 1);
          }}
          showViewSwitch={data.kind === 'graph' && showDataPreview}
          view3D={view3D}
          setView3D={setView3D}
          canFitView={data.kind !== 'vector' && !showDataPreview}
          showDataModeSwitch={isGraphDialect || isVectorDialect}
          dataMode={dataMode}
          setDataMode={setDataMode}
          isFullscreen={isFullscreen}
          onToggleFullscreen={onToggleFullscreen}
          canFullscreen={canFullscreen}
        />

        {legendVisible && <Legend kind={data.kind} />}

        <ViewToggles
          minimapVisible={minimapVisible}
          legendVisible={legendVisible}
          onToggleMinimap={toggleMinimapVisible}
          onToggleLegend={toggleLegendVisible}
          // Minimap lives inside React Flow — only the relational and graph
          // views mount React Flow. Other dialect-specific views render their
          // own layouts without a minimap, so the toggle would be a no-op.
          canToggleMinimap={
            !showDataPreview && (data.kind === 'relational' || data.kind === 'graph')
          }
        />
      </motion.div>
    </ReactFlowProvider>
  );
}

function totalSearchableFor(data: UnifiedSchema): number {
  switch (data.kind) {
    case 'relational':
      return data.tables.length;
    case 'graph':
      return data.labels.length + data.relationships.length;
    case 'vector':
      return data.collections.length;
    case 'keyvalue':
      return data.namespaces.length;
    case 'search':
      return data.indices.length;
    case 'document':
      return data.collections.length;
  }
}

function searchPlaceholderFor(kind: string): string {
  switch (kind) {
    case 'graph':
      return 'Filter labels, relationships, properties…';
    case 'vector':
      return 'Filter collections, payload fields…';
    case 'keyvalue':
      return 'Filter namespaces, keys…';
    case 'search':
      return 'Filter indices, fields…';
    case 'document':
      return 'Filter collections, fields…';
    default:
      return 'Filter tables, columns…';
  }
}
