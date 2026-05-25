import { lazy, Suspense, useCallback, useEffect, useMemo, useRef, useState } from 'react';
import cytoscape from 'cytoscape';
import type { Collection, Core, EdgeSingular, NodeSingular } from 'cytoscape';
import { GraphChat } from '../components/ui/GraphChat';
import { Icon } from '../components/ui';

const Graph3D = lazy(() =>
  import('../components/ui/Graph3D').then((m) => ({ default: m.Graph3D }))
);
// @ts-expect-error — cytoscape-fcose ships no types.
import fcose from 'cytoscape-fcose';
import { useSearchParams } from 'react-router-dom';
import { api, AttackSurfaceResp, Finding, Severity } from '../lib/api';
import { FindingDetailModal } from '../components/ui/FindingDetailModal';
import { LAYOUT_OPTS, STYLE, severityRank } from './graph/styles';
import { buildElements } from './graph/build';
import { Toolbar, type Counts } from './graph/Toolbar';
import { FilterBar } from './graph/FilterBar';
import { SummaryStrip } from './graph/SummaryStrip';
import { Legend } from './graph/Legend';
import { ZoomControls } from './graph/ZoomControls';
import { EdgeDetailsPanel, NodeDetailsPanel } from './graph/Panels';
import { TableView } from './graph/TableView';
import { EmptyState, NoResultsState } from './graph/EmptyState';
import { HoverTooltip, type HoverInfo } from './graph/HoverTooltip';
import type { GraphSummaryStats, LayoutName, NodeType, Selected, ViewMode } from './graph/types';

cytoscape.use(fcose);

const TARGET_KEY = 'red_agent.last_target';
const CHAT_OPEN_KEY = 'red_agent.graph_chat.open';
const RISK_LENS_MIN_NODES = 60;

export function AttackSurface() {
  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<Core | null>(null);
  const wrapRef = useRef<HTMLDivElement>(null);
  const [params, setParams] = useSearchParams();

  const [target, setTarget] = useState<string>(
    () => params.get('target') ?? localStorage.getItem(TARGET_KEY) ?? ''
  );
  const viewMode = (params.get('view') as ViewMode | null) ?? 'graph';
  const layout = (params.get('layout') as LayoutName | null) ?? 'fcose';

  const [data, setData] = useState<AttackSurfaceResp | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<Selected | null>(null);
  const [showLegend, setShowLegend] = useState(true);
  const [hover, setHover] = useState<HoverInfo | null>(null);
  const [severities, setSeverities] = useState<Set<Severity>>(new Set());
  const [types, setTypes] = useState<Set<NodeType>>(new Set());
  const [filtersTouched, setFiltersTouched] = useState(false);
  const [graphQuery, setGraphQuery] = useState('');
  const [chatOpen, setChatOpen] = useState(() => localStorage.getItem(CHAT_OPEN_KEY) !== 'false');
  const [graph3dFocus, setGraph3dFocus] = useState<{
    id: string;
    label: string;
    display: string;
  } | null>(null);
  const [graph3dHighlight, setGraph3dHighlight] = useState<Set<string>>(() => new Set());
  const [findingModal, setFindingModal] = useState<{
    open: boolean;
    finding: Finding | null;
    loading: boolean;
    error: string | null;
  }>({ open: false, finding: null, loading: false, error: null });

  const nodeLabelById = useMemo(() => {
    const m = new Map<string, string>();
    for (const n of data?.nodes ?? []) m.set(n.data.id, n.data.label);
    return m;
  }, [data]);
  const nodeFocusById = useMemo(() => {
    const m = new Map<string, { id: string; label: string; display: string }>();
    for (const n of data?.nodes ?? []) {
      m.set(n.data.id, {
        id: n.data.id,
        label: n.data.label,
        display: n.data.display || n.data.id,
      });
    }
    return m;
  }, [data]);

  const openFindingDetail = useCallback(
    async (id: string) => {
      const label = nodeLabelById.get(id);
      if (label !== 'Vulnerability') return false;
      setFindingModal({ open: true, finding: null, loading: true, error: null });
      try {
        const ev = await api.getFindingEvidence(id, 1);
        setFindingModal({ open: true, finding: ev.finding, loading: false, error: null });
      } catch (err) {
        const msg = String(err);
        const is404 = /(^|\s)404\b/.test(msg);
        const stub = is404 ? buildStubFinding(id, data, target) : null;
        if (stub) {
          setFindingModal({ open: true, finding: stub, loading: false, error: null });
        } else {
          setFindingModal({ open: true, finding: null, loading: false, error: msg });
        }
      }
      return true;
    },
    [nodeLabelById, data, target]
  );

  const elements = useMemo(() => (data ? buildElements(data) : []), [data]);
  const graphMatches = useMemo(() => {
    const matches = new Set<string>();
    const q = graphQuery.trim().toLowerCase();
    if (!data || !q) return matches;
    for (const n of data.nodes) {
      const haystack =
        `${n.data.display ?? ''} ${n.data.id} ${n.data.label} ${n.data.severity ?? ''}`
          .toLowerCase()
          .trim();
      if (haystack.includes(q)) matches.add(n.data.id);
    }
    return matches;
  }, [data, graphQuery]);

  function setParam(k: string, v: string | null) {
    setParams(
      (p) => {
        if (v === null || v === '') p.delete(k);
        else p.set(k, v);
        return p;
      },
      { replace: true }
    );
  }

  const load = useCallback(
    async (t: string) => {
      setError(null);
      setLoading(true);
      setSelected(null);
      setGraph3dFocus(null);
      setGraph3dHighlight(new Set());
      try {
        const resp = await api.getAttackSurface(t);
        setData(resp);
        setGraphQuery('');
        if (!filtersTouched && shouldApplyRiskLens(resp)) {
          setSeverities(new Set<Severity>(['critical', 'high']));
          setTypes(new Set<NodeType>(['Target', 'Endpoint', 'Service', 'Vulnerability']));
        } else if (!filtersTouched) {
          setSeverities(new Set());
          setTypes(new Set());
        }
        localStorage.setItem(TARGET_KEY, t);
      } catch (err) {
        setError(String(err));
      } finally {
        setLoading(false);
      }
    },
    [filtersTouched]
  );

  // auto-load on mount when target present in URL
  useEffect(() => {
    if (target && data === null && !loading && !error) {
      void load(target);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    localStorage.setItem(CHAT_OPEN_KEY, String(chatOpen));
  }, [chatOpen]);

  // Build / rebuild cytoscape when graph view active and elements change
  useEffect(() => {
    if (viewMode !== 'graph' || !containerRef.current || elements.length === 0) return;
    const cy = cytoscape({
      container: containerRef.current,
      elements,
      layout: LAYOUT_OPTS[layout],
      wheelSensitivity: 0.2,
      style: STYLE,
      minZoom: 0.2,
      maxZoom: 2.4,
      hideEdgesOnViewport: elements.length > 350,
      textureOnViewport: elements.length > 250,
      motionBlur: elements.length > 250,
      boxSelectionEnabled: false,
      autoungrabify: elements.length > 650,
    });
    cyRef.current = cy;
    if (elements.length > 180) cy.edges().addClass('dense');

    cy.on('tap', 'node', (evt) => {
      const node = evt.target as NodeSingular;
      focusNode(cy, node);
      setSelected({
        ...selectedFromNode(node),
      });
      if (String(node.data('label') || '') === 'Vulnerability') {
        void openFindingDetail(node.id());
      }
    });

    cy.on('tap', 'edge', (evt) => {
      const edge = evt.target as EdgeSingular;
      cy.elements().removeClass('focus dim path');
      cy.elements().addClass('dim');
      setGraph3dFocus(null);
      const src = edge.source();
      const tgt = edge.target();
      edge.removeClass('dim').addClass('focus');
      src.removeClass('dim').addClass('focus');
      tgt.removeClass('dim').addClass('focus');
      setSelected({
        kind: 'edge',
        id: edge.id(),
        type: String(edge.data('type') || ''),
        source: src.id(),
        target: tgt.id(),
        sourceLabel: String(src.data('display') || src.id()),
        targetLabel: String(tgt.data('display') || tgt.id()),
      });
    });

    cy.on('tap', (evt) => {
      if (evt.target === cy) {
        clearFocus(cy, setSelected);
        setGraph3dFocus(null);
        setGraph3dHighlight(new Set());
      }
    });

    cy.on('mouseover', 'node', (evt) => {
      const node = evt.target as NodeSingular;
      const rect = wrapRef.current?.getBoundingClientRect();
      const pos = node.renderedPosition();
      setHover({
        x: pos.x,
        y: pos.y - (rect ? 0 : 0),
        label: String(node.data('label') || ''),
        display: String(node.data('display') || node.id()),
        severity: (node.data('severity') || null) as Severity | null,
      });
    });
    cy.on('mouseout', 'node', () => setHover(null));
    cy.on('pan zoom drag', () => setHover(null));

    return () => {
      cy.destroy();
      cyRef.current = null;
      setHover(null);
    };
  }, [elements, viewMode]);

  // re-run layout without rebuilding cytoscape
  useEffect(() => {
    const cy = cyRef.current;
    if (!cy || elements.length === 0) return;
    cy.layout(LAYOUT_OPTS[layout]).run();
  }, [layout, elements.length]);

  // apply visibility filter
  useEffect(() => {
    const cy = cyRef.current;
    if (!cy) return;
    cy.batch(() => {
      cy.elements().removeClass('hidden searchHit searchDim');
      const hidden = cy.nodes().filter((n) => {
        const lbl = String(n.data('label') || '');
        const sev = String(n.data('severity') || '');
        if (types.size > 0 && !types.has(lbl as NodeType)) return true;
        if (severities.size > 0 && sev && !severities.has(sev as Severity)) return true;
        return false;
      });
      hidden.addClass('hidden');
      cy.edges().forEach((e) => {
        if (e.source().hasClass('hidden') || e.target().hasClass('hidden')) e.addClass('hidden');
      });
      if (graphQuery.trim()) {
        cy.nodes().forEach((n) => {
          if (n.hasClass('hidden')) return;
          if (graphMatches.has(n.id())) n.addClass('searchHit');
          else n.addClass('searchDim');
        });
        cy.edges().forEach((e) => {
          if (e.hasClass('hidden')) return;
          if (e.source().hasClass('searchHit') || e.target().hasClass('searchHit')) {
            e.addClass('searchHit');
          } else {
            e.addClass('searchDim');
          }
        });
      }
    });
  }, [severities, types, elements, graphQuery, graphMatches]);

  // global keyboard shortcuts
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      const tag = (e.target as HTMLElement | null)?.tagName?.toLowerCase();
      if (tag === 'input' || tag === 'textarea' || tag === 'select') {
        if (e.key === 'Escape') (e.target as HTMLElement).blur();
        return;
      }
      const cy = cyRef.current;
      if (e.key === 'Escape') {
        if (cy) clearFocus(cy, setSelected);
        setGraph3dFocus(null);
        setGraph3dHighlight(new Set());
      } else if (e.key === 'f' || e.key === 'F') {
        cy?.fit(undefined, 40);
      } else if (e.key === '/') {
        e.preventDefault();
        document.getElementById(data ? 'ra-graph-search' : 'ra-target')?.focus();
      }
    }
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [data]);

  const counts: Counts = useMemo(() => {
    if (!data) return { nodes: 0, edges: 0, critical: 0, high: 0, hidden: 0 };
    let critical = 0;
    let high = 0;
    for (const n of data.nodes) {
      if (n.data.severity === 'critical') critical++;
      else if (n.data.severity === 'high') high++;
    }
    let hidden = 0;
    if (severities.size > 0 || types.size > 0) {
      for (const n of data.nodes) {
        const lbl = n.data.label as NodeType;
        if (types.size > 0 && !types.has(lbl)) hidden++;
        else if (severities.size > 0 && n.data.severity && !severities.has(n.data.severity))
          hidden++;
      }
    }
    return { nodes: data.nodes.length, edges: data.edges.length, critical, high, hidden };
  }, [data, severities, types]);

  const sortedNodes = useMemo(() => {
    if (!data) return [];
    return [...data.nodes].sort(
      (a, b) => severityRank(b.data.severity) - severityRank(a.data.severity)
    );
  }, [data]);

  const summaryStats: GraphSummaryStats | null = useMemo(() => {
    if (!data) return null;
    let vulnerabilities = 0;
    let criticalHigh = 0;
    let entryPoints = 0;
    let enrichments = 0;
    let maxCvss: number | null = null;

    for (const n of data.nodes) {
      if (n.data.label === 'Vulnerability') vulnerabilities++;
      if (n.data.severity === 'critical' || n.data.severity === 'high') criticalHigh++;
      if (['Target', 'Endpoint', 'Service', 'CloudResource', 'ApiSpec'].includes(n.data.label)) {
        entryPoints++;
      }
      if (typeof n.data.cvss === 'number') maxCvss = Math.max(maxCvss ?? 0, n.data.cvss);
    }
    for (const e of data.edges) {
      if (['MAPS_TO', 'DETECTED_BY', 'GOVERNED_BY', 'RUNS_AS', 'STORES'].includes(e.data.type)) {
        enrichments++;
      }
    }
    const exposureScore = Math.min(
      100,
      Math.round(
        criticalHigh * 18 +
          Math.max(0, vulnerabilities - criticalHigh) * 5 +
          entryPoints * 2 +
          (maxCvss ?? 0) * 3
      )
    );
    return {
      nodes: data.nodes.length,
      edges: data.edges.length,
      visibleNodes: Math.max(0, data.nodes.length - counts.hidden),
      vulnerabilities,
      criticalHigh,
      entryPoints,
      enrichments,
      maxCvss,
      exposureScore,
    };
  }, [data, counts.hidden]);

  const empty = !loading && !error && data === null;
  const noResults = !loading && data !== null && data.nodes.length === 0;

  function exportPng() {
    const cy = cyRef.current;
    if (!cy) return;
    const png = cy.png({ bg: '#0a0e14', full: true, output: 'blob', scale: 2 }) as Blob;
    const url = URL.createObjectURL(png);
    const a = document.createElement('a');
    a.href = url;
    a.download = `attack-surface_${target || 'graph'}.png`;
    a.click();
    URL.revokeObjectURL(url);
  }

  function highlightPathToTarget() {
    const cy = cyRef.current;
    if (!cy || !selected || selected.kind !== 'node') return;
    const targets = cy.nodes('[label = "Target"]');
    if (targets.length === 0) return;
    const start = cy.getElementById(selected.id) as NodeSingular;
    let best: { path: Collection; len: number } | null = null;
    targets.forEach((t) => {
      const r = cy.elements().aStar({ root: start, goal: t, directed: false });
      if (r.found) {
        const len = r.path.nodes().length;
        if (!best || len < best.len) best = { path: r.path, len };
      }
    });
    if (!best) return;
    cy.elements().removeClass('focus dim path');
    cy.elements().addClass('dim');
    (best as { path: Collection }).path.removeClass('dim').addClass('path');
  }

  function focusFirstGraphMatch() {
    const cy = cyRef.current;
    if (!cy) return;
    const first = cy.nodes('.searchHit').first();
    if (first.empty()) return;
    const node = first[0] as NodeSingular;
    focusNode(cy, node);
    setSelected(selectedFromNode(node));
    cy.fit(node.closedNeighborhood(), 80);
  }

  function focusGraphNodeById(id: string) {
    const focus = nodeFocusById.get(id) ?? null;
    if (viewMode === 'graph3d') {
      setGraph3dFocus(focus);
      setGraph3dHighlight(focus ? new Set([id]) : new Set());
    } else if (cyRef.current) {
      const n = cyRef.current.getElementById(id);
      if (n.nonempty()) {
        const node = n as NodeSingular;
        focusNode(cyRef.current, node);
        setSelected(selectedFromNode(node));
        cyRef.current.fit(node.closedNeighborhood(), 80);
      }
    }
    void openFindingDetail(id);
  }

  function clearActiveFocus() {
    clearFocus(cyRef.current, setSelected);
    setGraph3dFocus(null);
    setGraph3dHighlight(new Set());
  }

  const hasPathSource =
    selected?.kind === 'node' && selected.label !== 'Target' && (data?.nodes.length ?? 0) > 1;
  const activeFocus =
    viewMode === 'graph3d'
      ? graph3dFocus
      : selected?.kind === 'node'
        ? { id: selected.id, label: selected.label, display: selected.display }
        : null;

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
          onToggleSeverity={(s) => {
            setFiltersTouched(true);
            setSeverities((cur) => toggle(cur, s));
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

function focusNode(cy: Core, node: NodeSingular) {
  cy.elements().removeClass('focus dim path');
  cy.elements().addClass('dim');
  node.closedNeighborhood().removeClass('dim').addClass('focus');
}

function selectedFromNode(node: NodeSingular) {
  return {
    kind: 'node' as const,
    id: node.id(),
    label: String(node.data('label') || ''),
    display: String(node.data('display') || node.id()),
    severity: (node.data('severity') || null) as Severity | null,
    cvss: typeof node.data('cvss') === 'number' ? node.data('cvss') : null,
    neighbors: node.connectedEdges().length,
  };
}

function clearFocus(cy: Core | null, setSelected: (s: Selected | null) => void) {
  cy?.elements().removeClass('focus dim path');
  setSelected(null);
}

function zoomBy(cy: Core | null, factor: number) {
  if (!cy) return;
  cy.zoom({
    level: cy.zoom() * factor,
    renderedPosition: { x: cy.width() / 2, y: cy.height() / 2 },
  });
}

function toggle<T>(set: Set<T>, v: T): Set<T> {
  const next = new Set(set);
  if (next.has(v)) next.delete(v);
  else next.add(v);
  return next;
}

function shouldApplyRiskLens(data: AttackSurfaceResp): boolean {
  if (data.nodes.length < RISK_LENS_MIN_NODES) return false;
  return data.nodes.some((n) => n.data.severity === 'critical' || n.data.severity === 'high');
}

const SEVERITIES: ReadonlySet<Severity> = new Set(['info', 'low', 'medium', 'high', 'critical']);

function buildStubFinding(
  id: string,
  data: AttackSurfaceResp | null,
  target: string
): Finding | null {
  const node = data?.nodes.find((n) => n.data.id === id);
  if (!node || node.data.label !== 'Vulnerability') return null;
  const sevRaw = node.data.severity;
  const severity: Severity =
    typeof sevRaw === 'string' && SEVERITIES.has(sevRaw as Severity)
      ? (sevRaw as Severity)
      : 'info';
  const cvssRaw = node.data.cvss;
  const cvss =
    typeof cvssRaw === 'number'
      ? cvssRaw
      : typeof cvssRaw === 'string' && cvssRaw !== ''
        ? Number(cvssRaw)
        : null;
  const display = node.data.display || id;
  return {
    id,
    scanner: 'unknown',
    title: display,
    description:
      'This finding is no longer present in the relational store but remains in ' +
      'the graph. Triage actions are unavailable; data shown is reconstructed ' +
      'from the attack-surface graph.',
    severity,
    cvss_score: cvss != null && Number.isFinite(cvss) ? cvss : null,
    cwe: null,
    cve: null,
    target,
    endpoint: null,
    port: null,
    service: null,
    remediation: null,
    discovered_at: '',
    state: 'open',
    assignee: null,
    triaged_at: null,
    resolved_at: null,
    due_at: null,
    notes: null,
    risk_score: null,
    controls: [],
    external_ref: null,
    evidence: { partial: true, source: 'graph_fallback' },
    raw: {},
  };
}
