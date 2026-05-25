/**
 * Draw static cyberpunk grid background
 */

import { CanvasRenderContext } from '../types';
import { ANIMATION, CANVAS_COLORS } from '../constants';

export function drawGrid({ ctx, width, height }: CanvasRenderContext): void {
  ctx.strokeStyle = CANVAS_COLORS.GRID;
  ctx.lineWidth = 1;

  const gridSize = ANIMATION.GRID_SIZE;

  // Vertical lines (static)
  for (let x = 0; x <= width; x += gridSize) {
    ctx.beginPath();
    ctx.moveTo(x, 0);
    ctx.lineTo(x, height);
    ctx.stroke();
  }

  // Horizontal lines (static)
  for (let y = 0; y <= height; y += gridSize) {
    ctx.beginPath();
    ctx.moveTo(0, y);
    ctx.lineTo(width, y);
    ctx.stroke();
  }
}
