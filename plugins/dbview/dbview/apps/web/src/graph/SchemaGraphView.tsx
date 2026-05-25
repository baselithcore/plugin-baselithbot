import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Controls,
  MiniMap,
  ReactFlow,
  useReactFlow,
  type Edge,
  type Node,
  type NodeMouseHandler,
  useEdgesState,
  useNodesState,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import type { SchemaGraph } from '@dbview/shared';
import { TableNode, type FkTarget } from './TableNode.js';
import { clearLayoutCache, layoutSchema } from './layout.js';
import { useAppStore } from '../store/app.js';

const NODE_TYPES = { table: TableNode };

const SCHEMA_HUE_PALETTE = ['#2dd4bf', '#60a5fa', '#fbbf24', '#fb7185', '#a78bfa', '#34d399'];

function colorForSchema(schema: string): string {
  let h = 0;
  for (const c of schema) h = (h * 31 + c.charCodeAt(0)) >>> 0;
  return SCHEMA_HUE_PALETTE[h % SCHEMA_HUE_PALETTE.length]!;
}

interface Props {
  graph: SchemaGraph;
  highlightedTables?: Set<string>;
  matchedTables?: Set<string>;
  onSelectTable?: (tableId: string) => void;
  onSelectColumn?: (tableId: string, columnName: string) => void;
  /** Bumped by parent to force a clean re-layout (discards user drag positions). */
  layoutNonce?: number;
}

export function SchemaGraphView({
  graph,
  highlightedTables,
  matchedTables,
  onSelectTable,
  onSelectColumn,
  layoutNonce = 0,
}: Props) {
  const [hoverNodeId, setHoverNodeId] = useState<string | null>(null);
  const minimapVisible = useAppStore((s) => s.minimapVisible);
  const rf = useReactFlow();

  const fkTargetsByTable = useMemo(() => {
    const map: Record<string, Record<string, FkTarget>> = {};
    const nameById = new Map(graph.tables.map((t) => [t.id, t.name] as const));
    for (const e of graph.edges) {
      const m = (map[e.source] ??= {});
      m[e.sourceColumn] = {
        tableName: nameById.get(e.target) ?? e.target,
        columnName: e.targetColumn,
      };
    }
    return map;
  }, [graph]);

  const layout = useMemo(
    () => {
      // Refresh button bumps layoutNonce — drop the structural cache so the
      // recompute is genuine, not a cache hit by fingerprint.
      if (layoutNonce > 0) clearLayoutCache();
      return layoutSchema(graph.tables, graph.edges);
    },
    // layoutNonce intentionally invalidates the memo so a Refresh click
    // recomputes positions from scratch even when the schema bytes are identical.

    [graph, layoutNonce]
  );

  const computedNodes = useMemo<Node[]>(() => {
    return layout.nodes.map((n) => {
      const isMatched = matchedTables ? matchedTables.has(n.id) : true;
      const isHighlighted = highlightedTables?.has(n.id) ?? false;
      return {
        ...n,
        data: {
          ...(n.data as object),
          highlighted: isHighlighted,
          fkTargets: fkTargetsByTable[n.id],
          onSelectTable,
          onSelectColumn,
        },
        style: {
          opacity: isMatched ? 1 : 0.22,
          transition: 'opacity 200ms',
        },
      };
    });
  }, [layout, highlightedTables, matchedTables, fkTargetsByTable, onSelectTable, onSelectColumn]);

  const computedEdges = useMemo<Edge[]>(() => {
    return layout.edges.map((e) => {
      const isHot = !!(highlightedTables?.has(e.source) && highlightedTables?.has(e.target));
      const isHover =
        hoverNodeId !== null && (e.source === hoverNodeId || e.target === hoverNodeId);
      const dimmed =
        (matchedTables && (!matchedTables.has(e.source) || !matchedTables.has(e.target))) ||
        (hoverNodeId !== null && !isHover);
      const stroke = isHot ? 'rgb(45 212 191)' : isHover ? 'rgb(125 211 252)' : '#71717a';
      // Swap to the qualified long label when this edge is highlighted or its
      // endpoint is hovered. Idle state stays compact so labels don't overlap
      // when many FKs converge on the same target table.
      const labels = (e.data ?? {}) as { shortLabel?: string; longLabel?: string };
      const label = (isHot || isHover ? labels.longLabel : labels.shortLabel) ?? e.label;
      return {
        ...e,
        label,
        animated: isHot || isHover,
        style: {
          ...(e.style ?? {}),
          stroke,
          strokeWidth: isHot || isHover ? 2 : 1.5,
          opacity: dimmed ? 0.18 : 1,
          transition: 'opacity 200ms, stroke 150ms',
        },
        labelStyle: {
          fontSize: 10.5,
          fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace',
          fill: dimmed ? '#52525b' : isHot ? '#2dd4bf' : isHover ? '#7dd3fc' : '#e4e4e7',
          fontWeight: isHot || isHover ? 600 : 500,
        },
        labelBgStyle: {
          fill: dimmed ? 'transparent' : 'rgba(9, 9, 11, 0.95)',
          stroke: isHot
            ? 'rgb(45 212 191)'
            : isHover
              ? 'rgb(125 211 252)'
              : 'rgba(63, 63, 70, 0.8)',
          strokeWidth: isHot || isHover ? 1.5 : 1,
        },
        labelBgPadding: [6, 3],
        labelBgBorderRadius: 4,
      };
    });
  }, [layout, highlightedTables, matchedTables, hoverNodeId]);

  const [nodes, setNodes, onNodesChange] = useNodesState(computedNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(computedEdges);

  // Track whether the latest computedNodes came from a forced re-layout.
  // We compare against the most recently *applied* nonce so a fresh schema
  // load (graph changes) keeps preserving drag positions, but a Refresh click
  // (only nonce changes) discards them and re-runs dagre cleanly.
  const [appliedNonce, setAppliedNonce] = useState(layoutNonce);

  useEffect(() => {
    if (layoutNonce !== appliedNonce) {
      // Force re-layout: drop preserved positions, fit view to fresh layout.
      setNodes(computedNodes);
      setAppliedNonce(layoutNonce);
      requestAnimationFrame(() => rf.fitView({ padding: 0.2, duration: 350 }));
      return;
    }
    setNodes((current) => {
      const byId = new Map(current.map((node) => [node.id, node]));
      return computedNodes.map((node) => {
        const existing = byId.get(node.id);
        return existing
          ? { ...node, position: existing.position, selected: existing.selected }
          : node;
      });
    });
  }, [computedNodes, setNodes, layoutNonce, appliedNonce, rf]);

  useEffect(() => {
    setEdges(computedEdges);
  }, [computedEdges, setEdges]);

  const onNodeMouseEnter = useCallback<NodeMouseHandler>((_, node) => {
    setHoverNodeId(node.id);
  }, []);
  const onNodeMouseLeave = useCallback<NodeMouseHandler>(() => {
    setHoverNodeId(null);
  }, []);

  // Precompute the minimap color per table id once per schema; the MiniMap
  // calls this for every visible node on each pan/zoom, so the inner lookup
  // must be O(1) instead of a linear scan of `graph.tables`.
  const minimapColorById = useMemo(() => {
    const map = new Map<string, string>();
    for (const t of graph.tables) map.set(t.id, colorForSchema(t.schema));
    return map;
  }, [graph.tables]);
  const minimapNodeColor = useCallback(
    (node: Node) => minimapColorById.get(node.id) ?? '#3f3f46',
    [minimapColorById]
  );

  return (
    <ReactFlow
      nodes={nodes}
      edges={edges}
      onNodesChange={onNodesChange}
      onEdgesChange={onEdgesChange}
      onNodeMouseEnter={onNodeMouseEnter}
      onNodeMouseLeave={onNodeMouseLeave}
      nodeTypes={NODE_TYPES}
      fitView
      fitViewOptions={{ padding: 0.2 }}
      minZoom={0.1}
      maxZoom={2}
      nodesConnectable={false}
      proOptions={{ hideAttribution: true }}
    >
      <Controls className="!bg-surface-1 !border-zinc-800" position="bottom-right" />
      {minimapVisible && (
        <MiniMap
          nodeColor={minimapNodeColor}
          nodeStrokeWidth={2}
          maskColor="rgba(9,9,11,0.82)"
          className="!bg-surface-1 !border-zinc-800"
          position="bottom-left"
          pannable
          zoomable
        />
      )}
    </ReactFlow>
  );
}
