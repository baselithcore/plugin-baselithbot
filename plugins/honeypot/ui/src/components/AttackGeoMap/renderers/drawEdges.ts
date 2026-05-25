/**
 * Draw edges (connections) and particles between nodes
 */

import { CanvasRenderContext } from '../types';
import { GraphNode, GraphEdge } from '../../types';
import { severityColors, ANIMATION } from '../constants';

interface DrawEdgesParams extends CanvasRenderContext {
  edges: Map<string, GraphEdge>;
  nodes: Map<string, GraphNode>;
}

export function drawEdges({ ctx, centerX, centerY, time, edges, nodes }: DrawEdgesParams): void {
  edges.forEach((edge) => {
    // Skip invisible edges
    if (edge.visible === false) return;

    const source = nodes.get(edge.source);
    const target = nodes.get(edge.target);
    if (!source || !target) return;

    const sx = centerX + source.x;
    const sy = centerY + source.y;
    const tx = centerX + target.x;
    const ty = centerY + target.y;

    const color = severityColors[edge.severity] || severityColors.info;

    // Calculate alpha based on activity - but always keep a minimum visibility
    const timeSinceActivity = Date.now() - edge.lastActivity;
    const activityAlpha = Math.max(0.3, 1 - timeSinceActivity / ANIMATION.EDGE_FADE_DURATION);

    // Deactivate edge only after fade duration
    if (timeSinceActivity > ANIMATION.EDGE_FADE_DURATION) {
      edge.active = false;
    }

    const pulse = (Math.sin(time * ANIMATION.EDGE_PULSE_FREQ) + 1) / 2;

    // Draw base line (always visible, slightly transparent)
    ctx.beginPath();
    ctx.moveTo(sx, sy);
    ctx.lineTo(tx, ty);
    const baseAlphaHex = Math.floor(activityAlpha * 180)
      .toString(16)
      .padStart(2, '0');
    ctx.strokeStyle = color + baseAlphaHex;
    ctx.lineWidth = 3;
    ctx.lineCap = 'round';
    ctx.stroke();

    // Draw pulsing gradient overlay for active edges
    if (edge.active) {
      const edgeGrad = ctx.createLinearGradient(sx, sy, tx, ty);
      const pulseAlpha = Math.floor(pulse * activityAlpha * 255)
        .toString(16)
        .padStart(2, '0');
      edgeGrad.addColorStop(0, color + pulseAlpha);
      edgeGrad.addColorStop(0.5, color + 'ff');
      edgeGrad.addColorStop(1, color + pulseAlpha);

      ctx.beginPath();
      ctx.moveTo(sx, sy);
      ctx.lineTo(tx, ty);
      ctx.strokeStyle = edgeGrad;
      ctx.lineWidth = 2;
      ctx.stroke();
    }

    // Draw and update particles (data packets flowing)
    // Use reverse iteration for safe removal during loop
    for (let i = edge.particles.length - 1; i >= 0; i--) {
      const p = edge.particles[i];
      p.progress += p.speed;

      // Remove completed particles
      if (p.progress >= 1) {
        edge.particles.splice(i, 1);
        continue;
      }

      // Skip rendering if particle hasn't started yet (e.g. for staggered bursts)
      if (p.progress < 0) continue;

      const px = sx + (tx - sx) * p.progress;
      const py = sy + (ty - sy) * p.progress;

      // Particle glow
      ctx.beginPath();
      ctx.arc(px, py, 6, 0, Math.PI * 2);
      const glowGrad = ctx.createRadialGradient(px, py, 0, px, py, 6);
      glowGrad.addColorStop(0, color);
      glowGrad.addColorStop(1, color + '00');
      ctx.fillStyle = glowGrad;
      ctx.fill();

      // Particle core
      ctx.beginPath();
      ctx.arc(px, py, 3, 0, Math.PI * 2);
      ctx.fillStyle = '#ffffff';
      ctx.shadowColor = color;
      ctx.shadowBlur = 10;
      ctx.fill();
      ctx.shadowBlur = 0;

      // Trail
      const trailLen = 0.08;
      const prevProgress = Math.max(0, p.progress - trailLen);
      const trailX = sx + (tx - sx) * prevProgress;
      const trailY = sy + (ty - sy) * prevProgress;

      ctx.beginPath();
      ctx.moveTo(px, py);
      ctx.lineTo(trailX, trailY);
      ctx.strokeStyle = color + '80';
      ctx.lineWidth = 2;
      ctx.stroke();
    }
  });
}
