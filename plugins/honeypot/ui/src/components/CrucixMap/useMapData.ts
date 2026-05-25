/**
 * useMapData - Transforms honeypot events/attackers into Crucix-style map data
 *
 * Produces points, arcs, and rings suitable for both Globe.gl (3D) and D3 (2D flat).
 */

import { useState, useEffect, useRef, useMemo } from 'react';
import type { AttackEvent, HoneypotAttacker } from '../types';
import type { MapPoint, MapArc, MapRing, MapStats, MapData } from './types';
import { getCountryCoordinates } from '../geoUtils/countryCoordinates';
import { getCountryFlag } from '../geoUtils';
import {
  SEVERITY_COLORS,
  SEVERITY_ARC_COLORS,
  SEVERITY_PRIORITY,
  HONEYPOT_DEFAULT_POSITION,
} from './constants';

/** Deterministic hash from a string – always returns the same value for the same input */
function deterministicHash(str: string, seed: number): number {
  let h = seed | 0;
  for (let i = 0; i < str.length; i++) {
    h = ((h << 5) - h + str.charCodeAt(i)) | 0;
  }
  return (h & 0xffff) / 0xffff; // 0..1
}

/** Jitter offset to spread overlapping points at the same country centroid */
function jitter(base: number, index: number, spread: number = 3): number {
  const angle = index * 137.508 * (Math.PI / 180); // golden angle
  const r = spread * Math.sqrt(index + 1) * 0.15;
  return base + r * Math.cos(angle);
}

function jitterLng(base: number, index: number, spread: number = 3): number {
  const angle = index * 137.508 * (Math.PI / 180);
  const r = spread * Math.sqrt(index + 1) * 0.15;
  return base + r * Math.sin(angle);
}

/** Map point size from attack count (logarithmic scale, clamped) */
function pointSize(attackCount: number): number {
  return Math.min(0.5, 0.1 + Math.log10(attackCount + 1) * 0.12);
}

/** Map arc stroke from attack count */
function arcStroke(attackCount: number): number {
  return Math.min(1.2, 0.3 + Math.log10(attackCount + 1) * 0.25);
}

/** Check if an event is recent (within last 5 minutes) */
function isRecent(timestamp: string): boolean {
  return Date.now() - new Date(timestamp).getTime() < 5 * 60 * 1000;
}

interface UseMapDataProps {
  events: AttackEvent[];
  attackers?: HoneypotAttacker[];
  activeProtocols?: string[];
}

export function useMapData({
  events = [],
  attackers = [],
  activeProtocols = [],
}: UseMapDataProps): MapData {
  const [attackVelocity, setAttackVelocity] = useState(0);
  const attackTimestampsRef = useRef<Date[]>([]);
  const prevAttackerIpsRef = useRef<string>('');

  // Track attack velocity
  useEffect(() => {
    // Record timestamps from new events
    events.forEach((e) => {
      const ts = new Date(e.timestamp);
      if (Date.now() - ts.getTime() < 120_000) {
        attackTimestampsRef.current.push(ts);
      }
    });

    // Trim to last 2000
    if (attackTimestampsRef.current.length > 2000) {
      attackTimestampsRef.current = attackTimestampsRef.current.slice(-2000);
    }
  }, [events]);

  // Velocity ticker
  useEffect(() => {
    const interval = setInterval(() => {
      const now = Date.now();
      const recent = attackTimestampsRef.current.filter((t) => now - t.getTime() < 60_000);
      setAttackVelocity(recent.length);
    }, 1000);
    return () => clearInterval(interval);
  }, []);

  // Clear timestamps on honeypot switch
  const attackerFingerprint = useMemo(
    () =>
      attackers
        .map((a) => a.ip)
        .sort()
        .join(','),
    [attackers]
  );

  useEffect(() => {
    const prev = prevAttackerIpsRef.current;
    if (prev && prev !== attackerFingerprint) {
      const isCompleteChange =
        attackerFingerprint === '' ||
        !attackerFingerprint.split(',').some((ip) => prev.includes(ip));
      if (isCompleteChange) {
        attackTimestampsRef.current = [];
        setAttackVelocity(0);
      }
    }
    prevAttackerIpsRef.current = attackerFingerprint;
  }, [attackerFingerprint]);

  // Build map data from attackers
  const { points, arcs, rings, stats } = useMemo(() => {
    const honeypot = HONEYPOT_DEFAULT_POSITION;
    const pts: MapPoint[] = [];
    const arcsArr: MapArc[] = [];
    const ringsArr: MapRing[] = [];
    const countrySet = new Set<string>();

    // Track index per country for jitter
    const countryIndexMap = new Map<string, number>();

    // Merge attacker data with event geo data for more precision
    const attackerGeoMap = new Map<string, { lat: number | null; lng: number | null }>();

    events.forEach((e) => {
      if (e.geo?.latitude && e.geo?.longitude) {
        attackerGeoMap.set(e.source_ip, {
          lat: e.geo.latitude,
          lng: e.geo.longitude,
        });
      }
    });

    // Process each attacker
    attackers.forEach((attacker) => {
      // Protocol filter
      if (
        activeProtocols.length > 0 &&
        !attacker.protocols.some((p) => activeProtocols.includes(p))
      ) {
        return;
      }

      const cc = attacker.country_code?.toUpperCase() || '';
      const eventGeo = attackerGeoMap.get(attacker.ip);
      const countryCoord = getCountryCoordinates(cc);

      // Check if IP is localhost or internal (for testing)
      const isLocalhost =
        attacker.ip === '127.0.0.1' ||
        attacker.ip === 'localhost' ||
        attacker.ip.startsWith('192.168.') ||
        attacker.ip.startsWith('10.') ||
        attacker.ip.startsWith('172.');

      // Determine position: prefer event geo > country centroid > localhost near honeypot > fallback
      let lat: number;
      let lng: number;

      if (eventGeo?.lat && eventGeo?.lng) {
        // Use exact event geo with deterministic jitter (same IP → same offset)
        lat = eventGeo.lat + (deterministicHash(attacker.ip, 1) - 0.5) * 0.5;
        lng = eventGeo.lng + (deterministicHash(attacker.ip, 2) - 0.5) * 0.5;
      } else if (countryCoord) {
        // Use country centroid with golden-angle jitter
        const idx = countryIndexMap.get(cc) ?? 0;
        countryIndexMap.set(cc, idx + 1);
        lat = jitter(countryCoord.lat, idx);
        lng = jitterLng(countryCoord.lng, idx);
      } else if (isLocalhost) {
        // Place localhost/internal IPs near honeypot for visibility in testing
        const idx = countryIndexMap.get('localhost') ?? 0;
        countryIndexMap.set('localhost', idx + 1);
        lat = honeypot.lat + (idx + 1) * 3;
        lng = honeypot.lng + (idx + 1) * 3;
      } else {
        // No geo data - place in Atlantic
        const fallbackIdx = pts.length;
        lat = 10 + (fallbackIdx % 10) * 3;
        lng = -30 + Math.floor(fallbackIdx / 10) * 3;
      }

      if (cc && cc !== 'UNK') countrySet.add(cc);

      const severity = attacker.max_severity || 'info';
      const color = SEVERITY_COLORS[severity] || SEVERITY_COLORS.info;
      const priority = SEVERITY_PRIORITY[severity] || 3;
      const recentAttack = isRecent(attacker.last_seen);
      const flag = getCountryFlag(cc);
      const protocol = attacker.protocols[0] || 'tcp';

      // Create point
      pts.push({
        id: `pt-${attacker.ip}`,
        lat,
        lng,
        size: pointSize(attacker.event_count),
        altitude:
          severity === 'critical'
            ? 0.06
            : severity === 'high'
              ? 0.035
              : severity === 'medium'
                ? 0.015
                : 0.005,
        color,
        ip: attacker.ip,
        country: attacker.country || 'Unknown',
        country_code: cc,
        severity,
        protocol,
        attackCount: attacker.event_count,
        priority,
        isRecent: recentAttack,
        popHead: `${flag} ${attacker.ip}`,
        popMeta: `${protocol.toUpperCase()} | ${severity.toUpperCase()} | ${attacker.event_count} attacks`,
        popText: `${attacker.country || 'Unknown'}${attacker.city ? ', ' + attacker.city : ''}`,
      });

      // Create arc
      const arcColors = SEVERITY_ARC_COLORS[severity] || SEVERITY_ARC_COLORS.info;
      arcsArr.push({
        id: `arc-${attacker.ip}`,
        startLat: lat,
        startLng: lng,
        endLat: honeypot.lat,
        endLng: honeypot.lng,
        color: arcColors,
        stroke: arcStroke(attacker.event_count),
        severity,
        protocol,
        attackCount: attacker.event_count,
      });

      // Create ring for critical/high or very active attackers
      if (severity === 'critical' || severity === 'high' || attacker.event_count > 50) {
        const fatScale = Math.log2(attacker.event_count + 1);
        ringsArr.push({
          lat,
          lng,
          maxR: Math.min(5, 1.5 + fatScale * 0.4),
          propagationSpeed: severity === 'critical' ? 2.0 : 1.5,
          repeatPeriod: severity === 'critical' ? 800 : 1200,
        });
      }
    });

    const totalEvents = attackers.reduce((sum, a) => sum + a.event_count, 0);

    // Debug logging
    if (pts.length > 0) {
      console.log('[CrucixMap] Generated points:', pts.length);
      console.log('[CrucixMap] First point:', pts[0]);
      console.log('[CrucixMap] Generated arcs:', arcsArr.length);
    }

    return {
      points: pts,
      arcs: arcsArr,
      rings: ringsArr,
      stats: {
        total: totalEvents,
        countries: countrySet.size,
        attackers: pts.length,
      } as MapStats,
    };
  }, [attackers, events, activeProtocols]);

  return {
    points,
    arcs,
    rings,
    honeypot: HONEYPOT_DEFAULT_POSITION,
    stats,
    attackVelocity,
  };
}
