/**
 * GeoUtils Utility Functions
 */

import type { ThreatLevel, MeshConnection, GeoMarker } from './types';

/**
 * Extract /24 subnet from IP address
 */
export function getSubnetFromIp(ip: string): string {
  if (!ip || ip === 'localhost') return 'local';

  // Handle IPv4
  const ipv4Match = ip.match(/^(\d{1,3}\.\d{1,3}\.\d{1,3})\.\d{1,3}$/);
  if (ipv4Match) {
    return ipv4Match[1] + '.0/24';
  }

  // Handle IPv6 - extract first 48 bits (/48)
  if (ip.includes(':')) {
    const parts = ip.split(':').slice(0, 3);
    return parts.join(':') + '::/48';
  }

  return 'unknown';
}

/**
 * Calculate mesh connections between markers from the same subnet
 */
export function calculateMeshConnections(markers: GeoMarker[]): MeshConnection[] {
  const connections: MeshConnection[] = [];
  const subnetGroups: Map<string, GeoMarker[]> = new Map();

  // Group markers by subnet
  markers.forEach((marker) => {
    const subnet = marker.subnet || 'unknown';
    if (!subnetGroups.has(subnet)) {
      subnetGroups.set(subnet, []);
    }
    subnetGroups.get(subnet)!.push(marker);
  });

  // Create connections within each subnet group
  subnetGroups.forEach((group, subnet) => {
    if (group.length < 2 || subnet === 'unknown' || subnet === 'local') return;

    // Connect all pairs within the group
    for (let i = 0; i < group.length; i++) {
      for (let j = i + 1; j < group.length; j++) {
        const markerA = group[i];
        const markerB = group[j];

        // Calculate distance-based strength (closer = stronger)
        const dist = Math.sqrt(
          Math.pow(markerA.lat - markerB.lat, 2) + Math.pow(markerA.lng - markerB.lng, 2)
        );
        const strength = Math.max(0.2, 1 - dist / 100);

        connections.push({
          id: `mesh-${i}-${j}-${subnet}`,
          sourceA: { lat: markerA.lat, lng: markerA.lng },
          sourceB: { lat: markerB.lat, lng: markerB.lng },
          strength,
          commonSubnet: subnet,
        });
      }
    }
  });

  return connections;
}

/**
 * Get threat level from attacks per minute
 */
export function getThreatLevel(attacksPerMinute: number): ThreatLevel {
  if (attacksPerMinute >= 50) return 5;
  if (attacksPerMinute >= 20) return 4;
  if (attacksPerMinute >= 10) return 3;
  if (attacksPerMinute >= 5) return 2;
  return 1;
}

/**
 * Get color for threat level
 */
export function getThreatLevelColor(level: ThreatLevel): string {
  switch (level) {
    case 5:
      return '#ff073a'; // Critical red
    case 4:
      return '#ff6b35'; // High orange
    case 3:
      return '#ffbe0b'; // Medium yellow
    case 2:
      return '#00ff88'; // Low green
    case 1:
      return '#00d4ff'; // Info cyan
  }
}

/**
 * Get label for threat level
 */
export function getThreatLevelLabel(level: ThreatLevel): string {
  switch (level) {
    case 5:
      return 'CRITICAL';
    case 4:
      return 'SEVERE';
    case 3:
      return 'ELEVATED';
    case 2:
      return 'GUARDED';
    case 1:
      return 'NORMAL';
  }
}

/**
 * Calculate attack velocity (attacks per minute)
 */
export function calculateAttackVelocity(timestamps: Date[], windowMinutes: number = 1): number {
  const now = new Date();
  const windowMs = windowMinutes * 60 * 1000;
  const recentAttacks = timestamps.filter((t) => now.getTime() - t.getTime() < windowMs);
  return recentAttacks.length;
}

/**
 * Format large numbers with K/M suffix
 */
export function formatAttackCount(count: number): string {
  if (count >= 1000000) return `${(count / 1000000).toFixed(1)}M`;
  if (count >= 1000) return `${(count / 1000).toFixed(1)}K`;
  return count.toString();
}

/**
 * Generate bezier curve control point for attack arcs
 */
export function getArcControlPoint(
  startX: number,
  startY: number,
  endX: number,
  endY: number,
  curvature: number = 0.3
): { x: number; y: number } {
  const midX = (startX + endX) / 2;
  const midY = (startY + endY) / 2;
  const distance = Math.sqrt(Math.pow(endX - startX, 2) + Math.pow(endY - startY, 2));

  // Curve upward for visual appeal
  return {
    x: midX,
    y: midY - distance * curvature,
  };
}

/**
 * Get color for protocol
 */
export function getProtocolColor(protocol: string | undefined): string {
  if (!protocol) return protocolColors.default;
  return protocolColors[protocol.toLowerCase()] || protocolColors.default;
}

/**
 * Enhanced severity colors with gradients
 */
export const severityGradients: Record<string, { start: string; end: string }> = {
  critical: { start: '#ff073a', end: '#ff4757' },
  high: { start: '#ff6b35', end: '#ffa502' },
  medium: { start: '#ffbe0b', end: '#ffe066' },
  low: { start: '#00ff88', end: '#7bed9f' },
  info: { start: '#00d4ff', end: '#70a1ff' },
};

/**
 * Protocol colors for node differentiation
 */
export const protocolColors: Record<string, string> = {
  ssh: '#f59e0b', // Amber
  http: '#3b82f6', // Blue
  https: '#3b82f6', // Blue
  tcp: '#8b5cf6', // Violet
  udp: '#10b981', // Emerald
  ftp: '#ec4899', // Pink
  smtp: '#6366f1', // Indigo
  dns: '#14b8a6', // Teal
  telnet: '#ef4444', // Red
  default: '#6b7280', // Gray
};
