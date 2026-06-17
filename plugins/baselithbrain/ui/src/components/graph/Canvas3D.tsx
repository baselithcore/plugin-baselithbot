import { useMemo, useRef } from 'react';
import ForceGraph3D from 'react-force-graph-3d';
import SpriteText from 'three-spritetext';
import { cloneGraph, edgeColor, nodeColor, type RenderProps } from './style';

/**
 * 3D (Three.js/WebGL) force graph. Each node carries a text sprite label and a
 * colored sphere (nodeThreeObjectExtend keeps both). Transparent background so
 * the themed container shows through in light + dark. Click a node to open it.
 */
export function Canvas3D({ data, activeId, width, height, onNode }: RenderProps) {
  const ref = useRef<any>(null);
  const graph = useMemo(() => cloneGraph(data), [data]);

  return (
    <ForceGraph3D
      ref={ref}
      width={width}
      height={height}
      graphData={graph}
      backgroundColor="rgba(0,0,0,0)"
      showNavInfo={false}
      nodeRelSize={5}
      nodeOpacity={0.95}
      linkColor={(l: any) => edgeColor(l)}
      linkOpacity={0.5}
      linkWidth={(l: any) => (l.kind === 'derived' ? 0.3 : 0.6)}
      nodeColor={(n: any) => nodeColor(n, activeId)}
      onNodeClick={(n: any) => onNode(n.id)}
      nodeThreeObjectExtend
      nodeThreeObject={(node: any) => {
        const sprite = new SpriteText(String(node.label || node.id).slice(0, 24));
        sprite.color = node.id === activeId ? '#ec4899' : 'rgba(150,150,170,0.95)';
        sprite.textHeight = 4;
        (
          sprite as unknown as { position: { set: (x: number, y: number, z: number) => void } }
        ).position.set(0, 8, 0);
        return sprite;
      }}
    />
  );
}
