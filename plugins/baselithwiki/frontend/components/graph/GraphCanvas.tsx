/**
 * View-mode dispatcher for the knowledge-graph canvas.
 *
 * Three renderers share the same filter / selection contract:
 *   - `2d` : react-force-graph-2d  (default, dense + fast, hover highlights)
 *   - `3d` : react-force-graph-3d  (spatial exploration via three.js)
 *   - `cose`: Cytoscape + cose-bilkent (deterministic layout, stable across reloads)
 *
 * The `ViewModeToggle` overlay lives at top-right of the canvas so users
 * switch in-place without losing filter / selection state. View-specific
 * overlays (Legend, LabelToggle, HoverToggle) are mounted by each view.
 */

import type { GraphData, GraphNode } from '../../lib/api/graph';
import { CytoscapeView } from './views/CytoscapeView';
import { ForceGraph2DView } from './views/ForceGraph2DView';
import { ForceGraph3DView } from './views/ForceGraph3DView';
import { ViewModeToggle, type ViewMode } from './views/overlays';

export type { ViewMode } from './views/overlays';

interface GraphCanvasProps {
  data: GraphData;
  visibleKinds: Set<string>;
  visibleCommunities: Set<number>;
  confidenceMin: number;
  search: string;
  onSelectNode: (node: GraphNode | null) => void;
  selectedNodeId: string | null;
  viewMode: ViewMode;
  onViewModeChange: (mode: ViewMode) => void;
}

export function GraphCanvas({
  data,
  visibleKinds,
  visibleCommunities,
  confidenceMin,
  search,
  onSelectNode,
  selectedNodeId,
  viewMode,
  onViewModeChange,
}: GraphCanvasProps) {
  const shared = {
    data,
    visibleKinds,
    visibleCommunities,
    confidenceMin,
    search,
    onSelectNode,
    selectedNodeId,
  };

  return (
    <div className="relative h-full w-full" data-testid="graph-canvas">
      {viewMode === '2d' && <ForceGraph2DView {...shared} />}
      {viewMode === '3d' && <ForceGraph3DView {...shared} />}
      {viewMode === 'cose' && <CytoscapeView {...shared} />}
      <ViewModeToggle mode={viewMode} onChange={onViewModeChange} />
    </div>
  );
}
