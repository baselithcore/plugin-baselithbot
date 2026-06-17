import {
  Background,
  BackgroundVariant,
  Controls,
  ReactFlow,
  type Edge,
  type Node,
} from '@xyflow/react';
import { useMemo } from 'react';

import type { Bottleneck, ProcessGraph } from '../api/types';
import { buildFlow } from '../lib/layout';
import { ProcessNode } from './ProcessNode';

const nodeTypes = { process: ProcessNode };

interface ProcessFlowProps {
  process: ProcessGraph;
  bottlenecks: Bottleneck[];
}

/**
 * Interactive process map. Nodes are laid out by longest-path depth and tinted
 * live by their worst detected bottleneck, so operators see where a process is
 * breaking down at a glance.
 */
export function ProcessFlow({ process, bottlenecks }: ProcessFlowProps) {
  const { nodes, edges } = useMemo<{ nodes: Node[]; edges: Edge[] }>(
    () => buildFlow(process, bottlenecks),
    [process, bottlenecks]
  );

  return (
    <div className="h-full min-h-[28rem] w-full overflow-hidden rounded-lg border border-white/10 bg-neutral-950/45">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        fitView
        fitViewOptions={{ padding: 0.25 }}
        proOptions={{ hideAttribution: true }}
        minZoom={0.2}
        maxZoom={1.5}
        nodesDraggable
        nodesConnectable={false}
      >
        <Background
          variant={BackgroundVariant.Dots}
          gap={26}
          size={1}
          color="rgba(148,163,184,0.18)"
        />
        <Controls showInteractive={false} />
      </ReactFlow>
    </div>
  );
}
