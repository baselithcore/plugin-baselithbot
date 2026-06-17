import { useMemo, useRef } from 'react';
import ForceGraph2D from 'react-force-graph-2d';
import { cloneGraph, edgeColor, nodeColor, type RenderProps } from './style';

/** 2D canvas force graph. Labels fade in on zoom; click a node to open it. */
export function Canvas2D({ data, activeId, width, height, onNode }: RenderProps) {
  const ref = useRef<any>(null);
  const graph = useMemo(() => cloneGraph(data), [data]);

  return (
    <ForceGraph2D
      ref={ref}
      width={width}
      height={height}
      graphData={graph}
      cooldownTicks={80}
      nodeRelSize={5}
      linkColor={(l: any) => edgeColor(l)}
      linkWidth={(l: any) => (l.kind === 'derived' ? 0.6 : 1)}
      nodeColor={(n: any) => nodeColor(n, activeId)}
      onNodeClick={(n: any) => onNode(n.id)}
      nodeCanvasObjectMode={() => 'after'}
      nodeCanvasObject={(node: any, ctx, scale) => {
        if (scale < 1.4 && node.kind !== 'moc' && node.id !== activeId) return;
        const label = String(node.label || node.id).slice(0, 24);
        ctx.font = `${11 / scale}px Inter, sans-serif`;
        ctx.fillStyle = 'rgba(140,140,160,0.95)';
        ctx.textAlign = 'center';
        ctx.fillText(label, node.x, node.y + 9 / scale);
      }}
    />
  );
}
