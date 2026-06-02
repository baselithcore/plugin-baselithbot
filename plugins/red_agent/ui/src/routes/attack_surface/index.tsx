import { lazy, Suspense } from 'react';
import { GraphChat } from '../../components/ui/GraphChat';
import { Icon } from '../../components/ui';
import { FindingDetailModal } from '../../components/ui/FindingDetailModal';
import { LAYOUT_OPTS } from '../graph/styles';
import { Toolbar } from '../graph/Toolbar';
import { FilterBar } from '../graph/FilterBar';
import { SummaryStrip } from '../graph/SummaryStrip';
import { Legend } from '../graph/Legend';
import { ZoomControls } from '../graph/ZoomControls';
import { EdgeDetailsPanel, NodeDetailsPanel } from '../graph/Panels';
import { TableView } from '../graph/TableView';
import { EmptyState, NoResultsState } from '../graph/EmptyState';
import { HoverTooltip } from '../graph/HoverTooltip';
import type { Severity } from '../../lib/api';
import type { NodeType } from '../graph/types';
import { clearFocus, toggle, zoomBy, TARGET_KEY } from './cy_helpers';
import { useSurfaceState } from './use_surface_state';

const Graph3D = lazy(() =>
  import('../../components/ui/Graph3D').then((m) => ({ default: m.Graph3D }))
);

export function AttackSurface() {
  const s = useSurfaceState();
  const {
    containerRef,
    cyRef,
    wrapRef,
    target,
    setTarget,
    viewMode,
    layout,
    data,
    setData,
    loading,
    error,
    setError,
    selected,
    setSelected,
    showLegend,
    setShowLegend,
    hover,
    severities,
    setSeverities,
    types,
    setTypes,
    setFiltersTouched,
    graphQuery,
    setGraphQuery,
    chatOpen,
    setChatOpen,
    graph3dHighlight,
    setGraph3dHighlight,
    setGraph3dFocus,
    findingModal,
    setFindingModal,
    graphMatches,
    setParam,
    load,
    counts,
    sortedNodes,
    summaryStats,
    empty,
    noResults,
    exportPng,
    highlightPathToTarget,
    focusFirstGraphMatch,
    focusGraphNodeById,
    clearActiveFocus,
    hasPathSource,
    activeFocus,
    openFindingDetail,
  } = s;

  return (
    <div className="flex h-full flex-col gap-4">
      <Toolbar
        target={target}
        onTargetChange={setTarget}
        onSubmit={() => {
          if (!target) return;
          setParam('target', target);
          void load(target);
        }}
        viewMode={viewMode}
        onViewMode={(v) => setParam('view', v === 'graph' ? null : v)}
        layout={layout}
        onLayout={(v) => setParam('layout', v === 'fcose' ? null : v)}
        loading={loading}
        counts={counts}
        onFit={() => cyRef.current?.fit(undefined, 40)}
        onReset={() => {
          if (!cyRef.current) return;
          clearFocus(cyRef.current, setSelected);
          cyRef.current.layout(LAYOUT_OPTS[layout]).run();
        }}
        onExport={exportPng}
        onClear={() => {
          setData(null);
          setSelected(null);
          setGraph3dFocus(null);
          setGraph3dHighlight(new Set());
          setFiltersTouched(false);
          setError(null);
          setTarget('');
          setParam('target', null);
          localStorage.removeItem(TARGET_KEY);
        }}
        hasData={data !== null && data.nodes.length > 0}
        graphQuery={graphQuery}
        onGraphQueryChange={setGraphQuery}
        graphMatches={graphMatches.size}
        onFocusGraphMatch={focusFirstGraphMatch}
      />

      {summaryStats && data !== null && data.nodes.length > 0 && (
        <SummaryStrip stats={summaryStats} />
      )}

      {data !== null && data.nodes.length > 0 && (
        <FilterBar
          severities={severities}
          types={types}
          hidden={counts.hidden}
          onToggleSeverity={(sev) => {
            setFiltersTouched(true);
            setSeverities((cur) => toggle(cur, sev));
          }}
          onToggleType={(t) => {
            setFiltersTouched(true);
            setTypes((cur) => toggle(cur, t));
          }}
          onCriticalPreset={() => {
            setFiltersTouched(true);
            setSeverities(new Set<Severity>(['critical', 'high']));
            setTypes(new Set<NodeType>(['Target', 'Endpoint', 'Service', 'Vulnerability']));
          }}
          onTopologyPreset={() => {
            setFiltersTouched(true);
            setSeverities(new Set());
            setTypes(
              new Set<NodeType>(['Target', 'CloudResource', 'Endpoint', 'Service', 'ApiSpec'])
            );
          }}
          onClear={() => {
            setFiltersTouched(true);
            setSeverities(new Set());
            setTypes(new Set());
          }}
        />
      )}

      {error && (
        <p
          role="alert"
          className="rounded border border-sev-critical/40 bg-sev-critical/10 px-3 py-2 text-sm text-sev-critical"
        >
          {error}
        </p>
      )}

      <div className="flex min-h-0 flex-1 flex-col gap-3 xl:flex-row">
        <div
          ref={wrapRef}
          className="relative min-h-[520px] flex-1 overflow-hidden rounded-lg border border-bg-line bg-bg-elevated xl:min-h-0"
        >
          <div
            aria-hidden
            className="pointer-events-none absolute inset-0 opacity-[0.07]"
            style={{
              backgroundImage: 'radial-gradient(circle at 1px 1px, #8b98b6 1px, transparent 0)',
              backgroundSize: '22px 22px',
            }}
          />
          {empty && (
            <EmptyState
              onPick={(t) => {
                setTarget(t);
                setParam('target', t);
                void load(t);
              }}
            />
          )}

          {loading && (
            <div className="absolute inset-0 z-10 grid place-items-center bg-bg-base/40 backdrop-blur-sm">
              <div className="font-display text-sm text-accent-neon">loading attack surface...</div>
            </div>
          )}

          {noResults && (
            <NoResultsState
              target={target}
              onClear={() => {
                setData(null);
                setError(null);
              }}
            />
          )}

          {data !== null && data.nodes.length > 0 && viewMode === 'graph' && (
            <>
              <div
                ref={containerRef}
                className="absolute inset-0"
                role="application"
                aria-label="attack surface graph"
              />
              <ZoomControls
                onIn={() => zoomBy(cyRef.current, 1.25)}
                onOut={() => zoomBy(cyRef.current, 1 / 1.25)}
                onFit={() => cyRef.current?.fit(undefined, 40)}
                onCenter={() => cyRef.current?.center()}
              />
              <Legend visible={showLegend} onToggle={() => setShowLegend((v) => !v)} />
              <HoverTooltip info={hover} />
              {selected?.kind === 'node' && (
                <NodeDetailsPanel
                  node={selected}
                  target={target}
                  onClose={() => clearFocus(cyRef.current, setSelected)}
                  onPathToTarget={highlightPathToTarget}
                  hasPath={hasPathSource}
                />
              )}
              {selected?.kind === 'edge' && (
                <EdgeDetailsPanel
                  edge={selected}
                  onClose={() => clearFocus(cyRef.current, setSelected)}
                />
              )}
            </>
          )}

          {data !== null && data.nodes.length > 0 && viewMode === 'graph3d' && (
            <Suspense
              fallback={
                <div className="absolute inset-0 grid place-items-center text-sm text-text-muted">
                  loading 3D graph…
                </div>
              }
            >
              <div className="absolute inset-0">
                <Graph3D
                  data={data}
                  highlightIds={graph3dHighlight}
                  onFocusChange={setGraph3dFocus}
                  onSelect={(id) => {
                    setGraph3dHighlight(id ? new Set([id]) : new Set());
                    if (id) void openFindingDetail(id);
                  }}
                />
              </div>
            </Suspense>
          )}

          {data !== null && data.nodes.length > 0 && viewMode === 'table' && (
            <TableView nodes={sortedNodes} />
          )}
        </div>

        {data !== null && data.nodes.length > 0 && (
          <aside
            className={`relative shrink-0 transition-[height,width] duration-200 ${
              chatOpen
                ? 'h-[420px] min-h-[360px] w-full xl:h-auto xl:min-h-0 xl:w-[400px]'
                : 'h-9 w-full xl:h-auto xl:w-9'
            }`}
          >
            <button
              type="button"
              onClick={() => setChatOpen((v) => !v)}
              aria-label={chatOpen ? 'Hide chat' : 'Show chat'}
              className="absolute right-2 top-2 z-10 grid h-7 w-7 place-items-center rounded-md border border-bg-line bg-bg-elevated/90 text-text-muted shadow-card transition hover:border-bg-line-strong hover:text-text-primary xl:-left-3 xl:right-auto xl:top-3 xl:h-6 xl:w-6 xl:rounded-full"
            >
              <Icon.ChevronRight size={13} aria-hidden className={chatOpen ? '' : 'rotate-180'} />
            </button>
            {chatOpen && (
              <GraphChat
                data={data}
                target={target}
                focus={activeFocus}
                onCitationClick={focusGraphNodeById}
                onClearFocus={clearActiveFocus}
              />
            )}
          </aside>
        )}
      </div>

      <FindingDetailModal
        finding={findingModal.finding}
        open={findingModal.open}
        onClose={() => setFindingModal({ open: false, finding: null, loading: false, error: null })}
      />
      {findingModal.open &&
        (findingModal.loading || findingModal.error) &&
        !findingModal.finding && (
          <div
            role="dialog"
            aria-modal="true"
            className="fixed inset-0 z-[60] grid place-items-center bg-bg-base/70 backdrop-blur-sm"
            onClick={() =>
              setFindingModal({ open: false, finding: null, loading: false, error: null })
            }
          >
            <div className="rounded-lg border border-bg-line bg-bg-elevated px-6 py-4 font-mono text-sm text-text-secondary shadow-2xl">
              {findingModal.loading ? (
                <span>Loading finding…</span>
              ) : (
                <span className="text-sev-critical">Failed to load: {findingModal.error}</span>
              )}
            </div>
          </div>
        )}
    </div>
  );
}
