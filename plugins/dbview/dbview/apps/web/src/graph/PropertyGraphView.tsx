import { useEffect, useMemo } from 'react';
import {
  Controls,
  MiniMap,
  ReactFlow,
  type Edge,
  type Node,
  useEdgesState,
  useNodesState,
} from '@xyflow/react';
import dagre from '@dagrejs/dagre';
import type { PropertyGraphSchema } from '@dbview/shared';
import { LabelNode } from './LabelNode.js';
import { useAppStore } from '../store/app.js';

const NODE_TYPES = { label: LabelNode };

const NODE_W = 220;
const NODE_H_BASE = 48;
const PROP_H = 22;

interface Props {
  graph: PropertyGraphSchema;
  highlightedLabels?: Set<string>;
  matchedLabels?: Set<string>;
  onSelectLabel?: (labelId: string) => void;
  onSelectProperty?: (labelId: string, propertyName: string) => void;
}

export function PropertyGraphView({
  graph,
  highlightedLabels,
  matchedLabels,
  onSelectLabel,
  onSelectProperty,
}: Props) {
  // Dagre layout is expensive on wide graphs and only depends on `graph`.
  // Style overlays (highlight / matched / opacity) re-run cheaply on top of
  // the cached positions, so changing the search filter or hovered label no
  // longer triggers a full re-layout.
  const layout = useMemo(() => layoutPropertyGraph(graph), [graph]);

  const { nodes: computedNodes, edges: computedEdges } = useMemo(
    () =>
      decoratePropertyGraph(
        graph,
        layout,
        highlightedLabels,
        matchedLabels,
        onSelectLabel,
        onSelectProperty
      ),
    [graph, layout, highlightedLabels, matchedLabels, onSelectLabel, onSelectProperty]
  );

  const [nodes, setNodes, onNodesChange] = useNodesState(computedNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(computedEdges);
  const minimapVisible = useAppStore((s) => s.minimapVisible);

  useEffect(() => {
    setNodes((current) => {
      const byId = new Map(current.map((node) => [node.id, node]));
      return computedNodes.map((node) => {
        const existing = byId.get(node.id);
        return existing
          ? {
              ...node,
              position: existing.position,
              selected: existing.selected,
            }
          : node;
      });
    });
  }, [computedNodes, setNodes]);

  useEffect(() => {
    setEdges(computedEdges);
  }, [computedEdges, setEdges]);

  return (
    <ReactFlow
      nodes={nodes}
      edges={edges}
      onNodesChange={onNodesChange}
      onEdgesChange={onEdgesChange}
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
          nodeColor={() => '#3f3f46'}
          maskColor="rgba(9,9,11,0.8)"
          className="!bg-surface-1 !border-zinc-800"
          position="bottom-left"
        />
      )}
    </ReactFlow>
  );
}

interface PropertyLayout {
  positionById: Map<string, { x: number; y: number; h: number }>;
}

function layoutPropertyGraph(graph: PropertyGraphSchema): PropertyLayout {
  const g = new dagre.graphlib.Graph({ multigraph: true });
  g.setGraph({ rankdir: 'LR', ranksep: 100, nodesep: 60 });
  g.setDefaultEdgeLabel(() => ({}));

  for (const l of graph.labels) {
    const h = NODE_H_BASE + l.properties.length * PROP_H;
    g.setNode(l.id, { width: NODE_W, height: h });
  }
  for (const r of graph.relationships) g.setEdge(r.source, r.target, {}, r.id);

  dagre.layout(g);

  const positionById = new Map<string, { x: number; y: number; h: number }>();
  for (const l of graph.labels) {
    const pos = g.node(l.id);
    const h = NODE_H_BASE + l.properties.length * PROP_H;
    positionById.set(l.id, { x: pos.x - NODE_W / 2, y: pos.y - h / 2, h });
  }
  return { positionById };
}

function decoratePropertyGraph(
  graph: PropertyGraphSchema,
  layout: PropertyLayout,
  highlighted?: Set<string>,
  matched?: Set<string>,
  onSelectLabel?: (id: string) => void,
  onSelectProperty?: (id: string, prop: string) => void
): { nodes: Node[]; edges: Edge[] } {
  // When user searches a relationship, surface its endpoint labels too.
  // Without this, an exact rel-type match would leave the rel visible
  // between two dimmed nodes — confusing.
  const matchedRelEndpoints = matched
    ? new Set(
        graph.relationships.filter((r) => matched.has(r.id)).flatMap((r) => [r.source, r.target])
      )
    : null;

  const nodes: Node[] = graph.labels.map((l) => {
    const pos = layout.positionById.get(l.id)!;
    const isMatched = matched
      ? matched.has(l.id) || (matchedRelEndpoints?.has(l.id) ?? false)
      : true;
    return {
      id: l.id,
      type: 'label',
      dragHandle: '.dbview-drag-handle',
      position: { x: pos.x, y: pos.y },
      data: {
        label: l,
        highlighted: highlighted ? highlighted.has(l.label) || highlighted.has(l.id) : false,
        onSelectLabel,
        onSelectProperty,
      },
      width: NODE_W,
      style: {
        opacity: isMatched ? 1 : 0.25,
        filter: isMatched ? undefined : 'grayscale(0.5)',
        transition: 'opacity 200ms, filter 200ms',
      },
    };
  });

  const edges: Edge[] = graph.relationships.map((r) => {
    const isHot = highlighted?.has(r.source) && highlighted?.has(r.target);
    const isMatch = matched?.has(r.id) ?? false;
    const endpointMatch = matched ? matched.has(r.source) || matched.has(r.target) : false;
    const dimmed = matched ? !isMatch && !endpointMatch : false;
    const emphasize = isHot || isMatch;
    return {
      id: r.id,
      source: r.source,
      target: r.target,
      type: 'smoothstep',
      label: r.type,
      animated: emphasize,
      labelBgStyle: { fill: '#18181b' },
      labelStyle: {
        fill: isMatch ? '#a5b4fc' : '#a1a1aa',
        fontSize: 11,
        fontWeight: emphasize ? 700 : 600,
      },
      markerEnd: { type: 'arrowclosed' as const },
      style: {
        stroke: emphasize ? 'rgb(99 102 241)' : '#71717a',
        strokeWidth: emphasize ? 2 : 1.5,
        opacity: dimmed ? 0.2 : 1,
        transition: 'opacity 200ms, stroke 150ms',
      },
    };
  });

  return { nodes, edges };
}
