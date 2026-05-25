/**
 * Draw radar sweep animation effect
 */

import { CanvasRenderContext } from '../types';
import { ANIMATION, CANVAS_COLORS } from '../constants';

export function drawRadarSweep({
  ctx,
  width,
  height,
  centerX,
  centerY,
  time,
  honeypotPosition,
}: CanvasRenderContext): void {
  ctx.save();

  // Use honeypot position if available, otherwise default to center
  // Note: honeypotPosition should be absolute canvas coordinates
  const originX = honeypotPosition ? honeypotPosition.x : centerX;
  const originY = honeypotPosition ? honeypotPosition.y : centerY;

  const radarAngle = (time * ANIMATION.RADAR_SPEED) % (Math.PI * 2);

  // Conic gradient sweep
  const radarGrad = ctx.createConicGradient(radarAngle, originX, originY);
  radarGrad.addColorStop(0, CANVAS_COLORS.RADAR_SWEEP);
  radarGrad.addColorStop(0.1, 'rgba(0, 212, 255, 0)');
  radarGrad.addColorStop(1, 'rgba(0, 212, 255, 0)');
  ctx.fillStyle = radarGrad;
  ctx.beginPath();
  // Large enough radius to cover screen
  ctx.arc(originX, originY, Math.max(width, height) * 1.5, 0, Math.PI * 2);
  ctx.fill();

  // Radar line
  ctx.strokeStyle = CANVAS_COLORS.RADAR_LINE;
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.moveTo(originX, originY);
  ctx.lineTo(
    originX + Math.cos(radarAngle) * Math.max(width, height) * 1.5,
    originY + Math.sin(radarAngle) * Math.max(width, height) * 1.5
  );
  ctx.stroke();

  ctx.restore();
}
