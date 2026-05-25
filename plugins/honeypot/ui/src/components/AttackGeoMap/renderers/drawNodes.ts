/**
 * Draw nodes (honeypot and attackers) with animations
 */

import { CanvasRenderContext } from '../types';
import { GraphNode } from '../../types';
import { ThreatLevel } from '../../geoUtils';
import { getCountryFlag, getThreatLevelColor } from '../../geoUtils';
import { severityColors, ANIMATION, NODE_DIMENSIONS, CANVAS_COLORS } from '../constants';

interface DrawNodesParams extends CanvasRenderContext {
  nodes: Map<string, GraphNode>;
  hoveredNodeId: string | null;
  selectedNodeId: string | null;
  draggingNodeId?: string | null;
  threatLevel: ThreatLevel;
}

/**
 * Draw all graph nodes (honeypot and attackers)
 */
export function drawNodes({
  ctx,
  centerX,
  centerY,
  time,
  nodes,
  hoveredNodeId,
  selectedNodeId,

  threatLevel,
}: DrawNodesParams): void {
  nodes.forEach((node) => {
    if (node.visible === false) return;

    const nx = centerX + node.x;
    const ny = centerY + node.y;
    const isHovered = hoveredNodeId === node.id;
    const isSelected = selectedNodeId === node.id;

    if (node.type === 'honeypot') {
      drawHoneypotNode(ctx, nx, ny, node, time, threatLevel);
    } else {
      drawAttackerNode(ctx, nx, ny, node, time, isHovered, isSelected);
    }
  });
}

/**
 * Draw the central honeypot node with animations
 */
function drawHoneypotNode(
  ctx: CanvasRenderingContext2D,
  nx: number,
  ny: number,
  node: GraphNode,
  time: number,
  threatLevel: ThreatLevel
): void {
  const pulse = Math.sin(time * ANIMATION.HONEYPOT_PULSE_SPEED) * 0.2 + 0.8;
  const threatColor = getThreatLevelColor(threatLevel);

  // Target Brackets for Honeypot
  ctx.save();
  ctx.translate(nx, ny);
  ctx.rotate(-time * ANIMATION.HONEYPOT_ROTATE_SPEED * 2.5);
  ctx.strokeStyle = CANVAS_COLORS.HONEYPOT_PRIMARY;
  ctx.lineWidth = 2;
  const hBracketSize = node.radius + 18;
  for (let i = 0; i < 4; i++) {
    ctx.rotate(Math.PI / 2);
    ctx.beginPath();
    ctx.moveTo(hBracketSize - 10, -hBracketSize);
    ctx.lineTo(hBracketSize, -hBracketSize);
    ctx.lineTo(hBracketSize, -hBracketSize + 10);
    ctx.stroke();
  }
  ctx.restore();

  // Slow breathing core glow
  const breath = Math.sin(time * ANIMATION.HONEYPOT_BREATH_SPEED) * 0.1 + 0.9;
  ctx.beginPath();
  ctx.arc(nx, ny, node.radius + 20, 0, Math.PI * 2);
  const shieldGrad = ctx.createRadialGradient(nx, ny, 0, nx, ny, node.radius + 20);
  shieldGrad.addColorStop(
    0,
    threatColor +
      Math.floor(breath * 50)
        .toString(16)
        .padStart(2, '0')
  );
  shieldGrad.addColorStop(1, threatColor + '00');
  ctx.fillStyle = shieldGrad;
  ctx.fill();

  // Rotating protective ring
  ctx.save();
  ctx.translate(nx, ny);
  ctx.rotate(time * ANIMATION.HONEYPOT_ROTATE_SPEED);
  ctx.beginPath();
  ctx.arc(0, 0, node.radius + 12, 0, Math.PI * 2);
  ctx.strokeStyle = threatColor + '60';
  ctx.lineWidth = 2;
  ctx.setLineDash([8, 12]);
  ctx.stroke();
  ctx.restore();

  // Glow
  ctx.beginPath();
  ctx.arc(nx, ny, node.radius + 10, 0, Math.PI * 2);
  const grad = ctx.createRadialGradient(nx, ny, 0, nx, ny, node.radius + 10);
  grad.addColorStop(0, `rgba(0, 255, 136, ${pulse * 0.3})`);
  grad.addColorStop(1, 'rgba(0, 255, 136, 0)');
  ctx.fillStyle = grad;
  ctx.fill();

  // Main circle
  ctx.beginPath();
  ctx.arc(nx, ny, node.radius, 0, Math.PI * 2);
  ctx.fillStyle = CANVAS_COLORS.HONEYPOT_BG;
  ctx.strokeStyle = CANVAS_COLORS.HONEYPOT_PRIMARY;
  ctx.lineWidth = 3;
  ctx.fill();
  ctx.stroke();

  // Icon & Label
  ctx.font = '24px Arial';
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  ctx.fillStyle = CANVAS_COLORS.HONEYPOT_PRIMARY;
  ctx.fillText('🍯', nx, ny);

  ctx.font = 'bold 10px sans-serif';
  ctx.fillStyle = CANVAS_COLORS.HONEYPOT_PRIMARY;
  ctx.fillText('HONEYPOT', nx, ny + node.radius + 15);
}

/**
 * Draw an attacker node with visual effects
 */
function drawAttackerNode(
  ctx: CanvasRenderingContext2D,
  nx: number,
  ny: number,
  node: GraphNode,
  time: number,
  isHovered: boolean,
  isSelected: boolean
): void {
  const color = severityColors[node.severity || 'info'] || severityColors.info;
  const baseRadius = NODE_DIMENSIONS.ATTACKER_BASE_RADIUS;

  const dynamicRadius = baseRadius + (isHovered ? 6 : 0) + (isSelected ? 4 : 0);

  // 1. subtle "sonar" ripple & impact shockwave
  const timeSinceAttack = Date.now() - (node.lastAttack?.getTime() || 0);

  // Shockwave impact (short, fast ripple on hit)
  if (timeSinceAttack < 1500) {
    const shockProgress = timeSinceAttack / 1500;
    const shockAlpha = 1 - shockProgress;
    const shockRadius = dynamicRadius + shockProgress * 40;

    ctx.beginPath();
    ctx.arc(nx, ny, shockRadius, 0, Math.PI * 2);
    ctx.strokeStyle = color;
    ctx.globalAlpha = shockAlpha * 0.8;
    ctx.lineWidth = 2;
    ctx.stroke();
    ctx.globalAlpha = 1.0;
  }

  // Persistent sonar for critical targets
  if (['critical', 'high'].includes(node.severity || '')) {
    const rippleAge = (time * 0.5) % 1;
    const rippleRadius = dynamicRadius + rippleAge * 30;
    const rippleAlpha = Math.max(0, 0.8 - rippleAge);

    ctx.beginPath();
    ctx.arc(nx, ny, rippleRadius, 0, Math.PI * 2);
    ctx.strokeStyle = color;
    ctx.globalAlpha = rippleAlpha * 0.6;
    ctx.lineWidth = 1.5;
    ctx.stroke();
    ctx.globalAlpha = 1.0;
  }

  // 2. Selection/Hover Ring
  if (isHovered || isSelected) {
    ctx.beginPath();
    ctx.arc(nx, ny, dynamicRadius + 8, 0, Math.PI * 2);
    ctx.strokeStyle = color;
    ctx.lineWidth = 1.5;
    ctx.setLineDash([3, 3]);
    ctx.stroke();
    ctx.setLineDash([]);
  }

  // 3. Node Body - Clearer, Stronger
  ctx.beginPath();
  ctx.arc(nx, ny, dynamicRadius, 0, Math.PI * 2);

  // Stronger Gradient for visibility
  const grad = ctx.createRadialGradient(nx, ny, 0, nx, ny, dynamicRadius);
  grad.addColorStop(0, color);
  grad.addColorStop(0.7, `${color}40`); // More opaque
  grad.addColorStop(1, `${color}10`);

  ctx.fillStyle = grad;
  ctx.fill();

  // Solid Core Ring
  ctx.beginPath();
  ctx.arc(nx, ny, dynamicRadius * 0.8, 0, Math.PI * 2);
  ctx.strokeStyle = color;
  ctx.lineWidth = 1.5;
  ctx.stroke();

  // Outer Glow
  ctx.beginPath();
  ctx.arc(nx, ny, dynamicRadius, 0, Math.PI * 2);
  ctx.strokeStyle = `${color}80`;
  ctx.lineWidth = 2;
  ctx.stroke();

  // 4. Content
  if (dynamicRadius > 15) {
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';

    // Flag
    ctx.font = '24px sans-serif';
    ctx.fillStyle = '#ffffff';
    ctx.shadowColor = 'rgba(0,0,0,0.8)';
    ctx.shadowBlur = 4;
    ctx.fillText(getCountryFlag(node.country_code), nx, ny);
    ctx.shadowBlur = 0;

    // 5. IP Badge - Fixed & Cleaner
    if (isHovered || isSelected || dynamicRadius > 20) {
      ctx.font = 'bold 11px "JetBrains Mono", monospace';
      let ipText = node.ip || 'UNKNOWN';
      let isLocal = false;

      if (ipText === '::1' || ipText === '127.0.0.1') {
        ipText = 'LOCALHOST';
        isLocal = true;
      } else if (!isHovered && !isSelected) {
        ipText = ipText.split('.').slice(0, 2).join('.') + '.*';
      }

      const textMetrics = ctx.measureText(ipText);
      const paddingX = 8;

      const badgeWidth = textMetrics.width + paddingX * 2;
      const badgeHeight = 20;
      const badgeY = ny + dynamicRadius + 10;
      const badgeX = nx - badgeWidth / 2;

      // Manual Rounded Rect (Safe implementation)
      const r = 4;
      ctx.beginPath();
      ctx.moveTo(badgeX + r, badgeY);
      ctx.lineTo(badgeX + badgeWidth - r, badgeY);
      ctx.quadraticCurveTo(badgeX + badgeWidth, badgeY, badgeX + badgeWidth, badgeY + r);
      ctx.lineTo(badgeX + badgeWidth, badgeY + badgeHeight - r);
      ctx.quadraticCurveTo(
        badgeX + badgeWidth,
        badgeY + badgeHeight,
        badgeX + badgeWidth - r,
        badgeY + badgeHeight
      );
      ctx.lineTo(badgeX + r, badgeY + badgeHeight);
      ctx.quadraticCurveTo(badgeX, badgeY + badgeHeight, badgeX, badgeY + badgeHeight - r);
      ctx.lineTo(badgeX, badgeY + r);
      ctx.quadraticCurveTo(badgeX, badgeY, badgeX + r, badgeY);
      ctx.closePath();

      ctx.fillStyle = '#0f172a'; // Deep dark blue/slate
      ctx.fill();

      ctx.strokeStyle = isLocal ? '#10b981' : '#475569'; // Emerald or Slate-600
      ctx.lineWidth = 1;
      ctx.stroke();

      // Text
      ctx.fillStyle = isLocal ? '#10b981' : '#94a3b8'; // Emerald or Slate-400
      ctx.fillText(ipText, nx, badgeY + badgeHeight / 2 + 1);
    }
  }
}
