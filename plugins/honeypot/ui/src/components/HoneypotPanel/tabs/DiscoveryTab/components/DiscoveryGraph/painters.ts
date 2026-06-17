import type { DiscoveryGraphNode } from '../../../../../types';
import { getNodeSize, getNodeColor, drawHexagon } from '../../utils/graphHelpers';

export function getCommunityColor(node: any): string {
  if (node.is_hub) return node.is_confirmed_cc ? '#ff4757' : '#ffaa00';

  // Use community_id for coloring if available
  if (node.community_id !== undefined) {
    const colors = [
      '#2ed573',
      '#1e90ff',
      '#a55eea',
      '#ffa502',
      '#00d2d3',
      '#ff6b81',
      '#7bed9f',
      '#70a1ff',
    ];
    return colors[node.community_id % colors.length];
  }
  return getNodeColor(node);
}

// Clean, minimal node rendering
export function paintNode(
  node: any,
  ctx: CanvasRenderingContext2D,
  globalScale: number,
  selectedNode: DiscoveryGraphNode | null,
  hoveredNode: DiscoveryGraphNode | null
): void {
  const size = getNodeSize(node);
  const color = getCommunityColor(node);
  const x = node.x || 0;
  const y = node.y || 0;
  const isSelected = selectedNode?.id === node.id;
  const isHovered = hoveredNode?.id === node.id;

  // Hub nodes: Hexagon shape
  if (node.is_hub) {
    // Main hexagon
    drawHexagon(ctx, x, y, size);

    // Fill with color
    ctx.fillStyle = color;
    ctx.fill();

    // Border: solid for confirmed, dashed for potential
    ctx.strokeStyle = '#ffffff';
    ctx.lineWidth = 2;
    if (!node.is_confirmed_cc) {
      ctx.setLineDash([3, 2]);
    }
    ctx.stroke();
    ctx.setLineDash([]);

    // Icon: ⚡ for confirmed, ? for potential
    ctx.fillStyle = '#ffffff';
    ctx.font = `bold ${Math.max(10, size * 0.5)}px Arial`;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(node.is_confirmed_cc ? '⚡' : '?', x, y);
  } else {
    // Regular nodes: Circle
    ctx.beginPath();
    ctx.arc(x, y, size, 0, 2 * Math.PI);
    ctx.fillStyle = color;
    ctx.fill();

    // Border based on Threat Score
    if (node.threat_score && node.threat_score > 0.7) {
      ctx.strokeStyle = '#ff4757'; // High threat red border
      ctx.lineWidth = 2;
    } else {
      ctx.strokeStyle = 'rgba(255, 255, 255, 0.6)';
      ctx.lineWidth = 1.5;
    }
    ctx.stroke();
  }

  // Selection ring
  if (isSelected || isHovered) {
    ctx.beginPath();
    ctx.arc(x, y, size + 4, 0, 2 * Math.PI);
    ctx.strokeStyle = isSelected ? '#00ffff' : '#ffffff';
    ctx.lineWidth = 2;
    ctx.stroke();
  }

  // Labels - show for hubs always, others on hover/zoom
  if (node.is_hub || isHovered || isSelected || globalScale > 2) {
    const label = node.id;
    let subLabel = '';
    if (node.ja4_fingerprint) subLabel = `JA4: ${node.ja4_fingerprint.substring(0, 8)}...`;

    const fontSize = 10;
    ctx.font = `600 ${fontSize}px Inter, sans-serif`;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'top';

    const textWidth = ctx.measureText(label).width;
    const padX = 4;
    const padY = 3;
    const labelY = y + size + 5;

    // Background
    ctx.fillStyle = 'rgba(0, 0, 0, 0.8)';
    ctx.beginPath();
    ctx.roundRect(
      x - textWidth / 2 - padX,
      labelY - padY,
      textWidth + padX * 2,
      (subLabel ? fontSize * 2 : fontSize) + padY * 2,
      3
    );
    ctx.fill();

    // Text
    ctx.fillStyle = '#ffffff';
    ctx.fillText(label, x, labelY);

    if (subLabel) {
      ctx.fillStyle = '#aaa';
      ctx.font = `400 ${fontSize - 1}px Inter, sans-serif`;
      ctx.fillText(subLabel, x, labelY + fontSize + 2);
    }
  }
}

// Simple link rendering
export function paintLink(link: any, ctx: CanvasRenderingContext2D): void {
  const start = link.source;
  const end = link.target;

  if (!start.x || !start.y || !end.x || !end.y) return;

  const isIntraCluster = link.is_intra_cluster;
  const color = isIntraCluster ? getNodeColor(start) : '#ffffff';
  const opacity = isIntraCluster ? 0.4 : 0.15;
  const lineWidth = isIntraCluster ? 1.5 : 1;

  ctx.beginPath();
  ctx.moveTo(start.x, start.y);
  ctx.lineTo(end.x, end.y);
  ctx.strokeStyle = isIntraCluster ? `${color}66` : `rgba(255, 255, 255, ${opacity})`;
  ctx.lineWidth = lineWidth;
  ctx.stroke();
}
