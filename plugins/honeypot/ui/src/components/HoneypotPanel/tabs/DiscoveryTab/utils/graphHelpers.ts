/**
 * Graph visualization helper functions
 */

import { CLUSTER_COLORS, SEVERITY_COLORS } from '../constants/graphConstants';
import type { AttackSeverity } from '../../../../types';

/**
 * Calculate node size based on degree, attack count, and hub status
 */
export function getNodeSize(node: any): number {
  const baseSize = 10;
  const degreeBonus = Math.min(node.degree * 0.5, 6);
  const attackBonus = Math.min(Math.log10(node.attack_count + 1) * 1.5, 4);
  const hubBonus = node.is_hub ? 8 : 0;
  return baseSize + degreeBonus + attackBonus + hubBonus;
}

/**
 * Get node color based on type and status
 */
export function getNodeColor(node: any): string {
  // Confirmed C&C: red
  if (node.is_hub && node.is_confirmed_cc) return '#ff4757';
  // Potential C&C: amber
  if (node.is_hub) return '#ffaa00';
  if (node.cluster_id !== null) {
    const idx = parseInt(node.cluster_id) % CLUSTER_COLORS.length;
    return CLUSTER_COLORS[idx];
  }
  return SEVERITY_COLORS[node.severity as AttackSeverity] || '#888888';
}

/**
 * Draw hexagon shape on canvas
 */
export function drawHexagon(ctx: CanvasRenderingContext2D, x: number, y: number, size: number) {
  ctx.beginPath();
  for (let i = 0; i < 6; i++) {
    const angle = (Math.PI / 3) * i - Math.PI / 2;
    const px = x + size * Math.cos(angle);
    const py = y + size * Math.sin(angle);
    if (i === 0) ctx.moveTo(px, py);
    else ctx.lineTo(px, py);
  }
  ctx.closePath();
}

/**
 * Convert country code to flag emoji
 */
export function getCountryFlag(countryCode: string): string {
  const codePoints = countryCode
    .toUpperCase()
    .split('')
    .map((char) => 127397 + char.charCodeAt(0));
  return String.fromCodePoint(...codePoints);
}
