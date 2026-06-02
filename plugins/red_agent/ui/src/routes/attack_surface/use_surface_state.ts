import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import cytoscape from 'cytoscape';
import type { Core, EdgeSingular, NodeSingular } from 'cytoscape';
// @ts-expect-error — cytoscape-fcose ships no types.
import fcose from 'cytoscape-fcose';
import { useSearchParams } from 'react-router-dom';
import { api, AttackSurfaceResp, Finding, Severity } from '../../lib/api';
import { LAYOUT_OPTS, STYLE } from '../graph/styles';
import { buildElements } from '../graph/build';
import type { Counts } from '../graph/Toolbar';
import type { HoverInfo } from '../graph/HoverTooltip';
import type { GraphSummaryStats, LayoutName, NodeType, Selected, ViewMode } from '../graph/types';
import { computeCounts, computeSortedNodes, computeSummaryStats } from './derived';
import {
  buildStubFinding,
  CHAT_OPEN_KEY,
  clearFocus,
  focusNode,
  selectedFromNode,
  shouldApplyRiskLens,
  TARGET_KEY,
} from './cy_helpers';

cytoscape.use(fcose);

export function useSurfaceState() {
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

  const counts: Counts = useMemo(
    () => computeCounts(data, severities, types),
    [data, severities, types]
  );

  const sortedNodes = useMemo(() => computeSortedNodes(data), [data]);

  const summaryStats: GraphSummaryStats | null = useMemo(
    () => computeSummaryStats(data, counts.hidden),
    [data, counts.hidden]
  );

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
    let best: { path: import('cytoscape').Collection; len: number } | null = null;
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
    (best as { path: import('cytoscape').Collection }).path.removeClass('dim').addClass('path');
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

  return {
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
  };
}
