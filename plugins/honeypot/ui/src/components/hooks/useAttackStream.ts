import { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { StreamAttackEvent, GraphNode, GraphEdge, AttackEvent, HoneypotAttacker } from '../types';
import { NODE_DIMENSIONS } from '../AttackGeoMap/constants';

// Severity priority for determining maximum severity (higher = more severe)
const SEVERITY_PRIORITY: Record<string, number> = {
  info: 1,
  low: 2,
  medium: 3,
  high: 4,
  critical: 5,
};

/** Returns the more severe of two severity levels */
function getMaxSeverity(a: string | undefined, b: string | undefined): string {
  const priorityA = SEVERITY_PRIORITY[a || 'info'] || 1;
  const priorityB = SEVERITY_PRIORITY[b || 'info'] || 1;
  return priorityA >= priorityB ? a || 'info' : b || 'info';
}

interface UseAttackStreamProps {
  activeProtocols?: string[];
  events: AttackEvent[];
  /** Aggregated attackers from backend - used to create persistent nodes */
  attackers?: HoneypotAttacker[];
}

export const useAttackStream = ({
  activeProtocols = [],
  events = [],
  attackers = [],
}: UseAttackStreamProps) => {
  const [stats, setStats] = useState({ total: 0, countries: 0, attackers: 0 });
  const [attackVelocity, setAttackVelocity] = useState(0);

  const nodesRef = useRef<Map<string, GraphNode>>(new Map());
  const edgesRef = useRef<Map<string, GraphEdge>>(new Map());
  const attackTimestampsRef = useRef<Date[]>([]);
  const processedEventIdsRef = useRef<Map<string, { hasGeo: boolean }>>(new Map());
  const initializedAttackersRef = useRef<Set<string>>(new Set());

  // Track attacker IPs to detect honeypot switch (complete data change)
  const prevAttackerIpsRef = useRef<string>('');

  // Create a fingerprint of current attackers to detect complete data change
  const attackerIpsFingerprint = useMemo(() => {
    return attackers
      .map((a) => a.ip)
      .sort()
      .join(',');
  }, [attackers]);

  // Reset all state when attackers data changes completely (honeypot switch)
  useEffect(() => {
    const prevFingerprint = prevAttackerIpsRef.current;
    const currentFingerprint = attackerIpsFingerprint;

    // Detect honeypot switch: fingerprint changed AND is now empty or completely different
    const isCompleteChange =
      prevFingerprint !== currentFingerprint &&
      (currentFingerprint === '' ||
        !currentFingerprint.split(',').some((ip) => prevFingerprint.includes(ip)));

    if (isCompleteChange && prevFingerprint !== '') {
      // Clear all visualization state
      nodesRef.current.clear();
      edgesRef.current.clear();
      processedEventIdsRef.current.clear();
      initializedAttackersRef.current.clear();
      attackTimestampsRef.current = [];

      // Re-initialize honeypot node
      nodesRef.current.set('honeypot', {
        id: 'honeypot',
        type: 'honeypot',
        x: 0,
        y: 0,
        vx: 0,
        vy: 0,
        radius: NODE_DIMENSIONS.HONEYPOT_RADIUS,
        visible: true,
      });

      // Reset stats
      setStats({ total: 0, countries: 0, attackers: 0 });
      setAttackVelocity(0);
    }

    prevAttackerIpsRef.current = currentFingerprint;
  }, [attackerIpsFingerprint]);

  // Initialize honeypot node
  useEffect(() => {
    if (!nodesRef.current.has('honeypot')) {
      nodesRef.current.set('honeypot', {
        id: 'honeypot',
        type: 'honeypot',
        x: 0,
        y: 0,
        vx: 0,
        vy: 0,
        radius: NODE_DIMENSIONS.HONEYPOT_RADIUS,
        visible: true,
      });
    }
  }, []);

  // Synchronize nodes with filtered attackers (persistent data from backend)
  // CRITICAL: This effect must handle both adding NEW nodes AND removing STALE nodes
  // when time filters change. Without the cleanup logic, nodes would persist on the
  // map even when no longer matching the current time filter.
  useEffect(() => {
    // Build set of valid IPs from current filtered attackers
    const validIps = new Set(attackers.map((a) => a.ip));

    // SYNC STEP: Remove nodes that are no longer in the filtered set
    // This ensures the graph stays synchronized with time filters
    for (const [nodeId, node] of nodesRef.current.entries()) {
      if (node.type === 'attacker' && node.ip && !validIps.has(node.ip)) {
        nodesRef.current.delete(nodeId);
        edgesRef.current.delete(`edge-${node.ip}`);
        initializedAttackersRef.current.delete(node.ip);
        processedEventIdsRef.current.delete(node.ip); // Also clear event tracking
      }
    }

    // Handle empty state (all filtered out)
    if (attackers.length === 0) {
      // Update stats to reflect empty state
      setStats({ total: 0, countries: 0, attackers: 0 });
      return;
    }

    let newNodesCreated = 0;

    attackers.forEach((attacker) => {
      const nodeId = `attacker-${attacker.ip}`;

      // Skip if we already created this node from attackers data
      if (initializedAttackersRef.current.has(attacker.ip)) {
        // But still update the node with latest data if it exists
        const existing = nodesRef.current.get(nodeId);
        if (existing) {
          existing.attackCount = attacker.event_count;
          existing.country_code = attacker.country_code || undefined;
          existing.country = attacker.country || undefined;
          // IMPORTANT: Use getMaxSeverity to prevent downgrading from live data to stale backend data
          existing.severity = getMaxSeverity(existing.severity, attacker.max_severity);
          // Update protocols array (use first for compatibility)
          if (attacker.protocols.length > 0) {
            existing.protocol = attacker.protocols[0];
          }
        }
        return;
      }

      // Check if node already exists from recent events
      const existingNode = nodesRef.current.get(nodeId);

      if (existingNode) {
        // Update existing node with backend data (more accurate counts)
        existingNode.attackCount = attacker.event_count;
        if (!existingNode.country_code && attacker.country_code) {
          existingNode.country_code = attacker.country_code;
          existingNode.country = attacker.country || undefined;
        }
      } else {
        // Create new node from attacker data
        const angle = Math.random() * Math.PI * 2;
        const distance = 200 + Math.random() * 100;

        // Determine visibility based on active protocols
        const isVisible =
          activeProtocols.length === 0 ||
          attacker.protocols.some((p) => activeProtocols.includes(p));

        nodesRef.current.set(nodeId, {
          id: nodeId,
          type: 'attacker',
          x: Math.cos(angle) * distance,
          y: Math.sin(angle) * distance,
          vx: 0,
          vy: 0,
          radius: 25,
          ip: attacker.ip,
          country_code: attacker.country_code || undefined,
          country: attacker.country || undefined,
          protocol: attacker.protocols[0] || 'unknown',
          severity: attacker.max_severity,
          attackCount: attacker.event_count,
          lastAttack: new Date(attacker.last_seen),
          visible: isVisible,
        });

        // Create static edge (no particles for historical data)
        const edgeId = `edge-${attacker.ip}`;
        if (!edgesRef.current.has(edgeId)) {
          edgesRef.current.set(edgeId, {
            source: nodeId,
            target: 'honeypot',
            active: false,
            lastActivity: new Date(attacker.last_seen).getTime(),
            protocol: attacker.protocols[0] || 'unknown',
            severity: attacker.max_severity,
            visible: isVisible,
            particles: [],
          });
        }

        newNodesCreated++;
      }

      initializedAttackersRef.current.add(attacker.ip);
    });

    // Update stats based on attackers data
    if (newNodesCreated > 0 || attackers.length > 0) {
      const uniqueCountries = new Set(
        attackers.map((a) => a.country_code).filter((cc): cc is string => !!cc && cc !== 'UNK')
      ).size;

      const totalEvents = attackers.reduce((sum, a) => sum + a.event_count, 0);

      const uniqueAttackers = new Set(attackers.map((a) => a.ip)).size;

      setStats({
        total: totalEvents,
        countries: uniqueCountries,
        attackers: uniqueAttackers,
      });
    }
  }, [attackers, activeProtocols]);

  const addAttackerNode = useCallback(
    (attack: StreamAttackEvent) => {
      // We process all attacks to keep stats correct, but we might hide them
      const nodeId = `attacker-${attack.source_ip}`;
      const existing = nodesRef.current.get(nodeId);
      const countIncrement = attack.attackCount || 1;

      // Check if protocol is active for visibility
      const isProtocolActive =
        activeProtocols.length === 0 || activeProtocols.includes(attack.protocol);

      if (existing) {
        existing.attackCount = (existing.attackCount || 0) + countIncrement;
        existing.lastAttack = new Date();
        // Keep the maximum severity seen from this attacker (don't downgrade)
        existing.severity = getMaxSeverity(existing.severity, attack.severity);
        existing.protocol = attack.protocol;
        existing.visible = isProtocolActive;
      } else {
        const angle = Math.random() * Math.PI * 2;
        const distance = 200 + Math.random() * 100;

        nodesRef.current.set(nodeId, {
          id: nodeId,
          type: 'attacker',
          x: Math.cos(angle) * distance,
          y: Math.sin(angle) * distance,
          vx: 0,
          vy: 0,
          radius: 25,
          ip: attack.source_ip,
          country_code: attack.country_code,
          country: attack.country,
          protocol: attack.protocol,
          severity: attack.severity,
          attackCount: countIncrement,
          lastAttack: new Date(),
          visible: isProtocolActive,
        });
      }

      const edgeId = `edge-${attack.source_ip}`;
      const existingEdge = edgesRef.current.get(edgeId);

      // Calculate packet count based on payload size (simulating visual MTU)
      const payloadSize =
        (attack.raw_data?.length || 0) +
        (attack.command?.length || 0) +
        (attack.http_body?.length || 0);
      // Base packets + 1 per 64 bytes of data, clamped to [1, 20]
      const calculatedPackets =
        Math.ceil(payloadSize / 64) + (attack.event_type === 'auth' ? 2 : 1);
      const burstCount = Math.min(Math.max(calculatedPackets, 1), 20);

      const baseSpeed = 0.02 + Math.random() * 0.01;
      const particles = Array.from({ length: burstCount }).map((_, i) => ({
        progress: -(i * 0.15), // Staggered start
        speed: baseSpeed + (Math.random() * 0.005 - 0.0025),
      }));

      if (existingEdge) {
        existingEdge.active = true;
        existingEdge.lastActivity = Date.now();
        existingEdge.protocol = attack.protocol;
        existingEdge.severity = getMaxSeverity(existingEdge.severity, attack.severity);
        existingEdge.visible = isProtocolActive;
        existingEdge.particles.push(...particles);
      } else {
        edgesRef.current.set(edgeId, {
          source: nodeId,
          target: 'honeypot',
          active: true,
          lastActivity: Date.now(),
          protocol: attack.protocol,
          severity: attack.severity,
          visible: isProtocolActive,
          particles,
        });
      }

      attackTimestampsRef.current.push(new Date());
      if (attackTimestampsRef.current.length > 2000) {
        attackTimestampsRef.current = attackTimestampsRef.current.slice(-2000);
      }
    },
    [activeProtocols]
  );

  // Process incoming events (for real-time animations)
  useEffect(() => {
    // Filter for new events or updates
    let newEventsCount = 0;
    events.forEach((event) => {
      const processedState = processedEventIdsRef.current.get(event.event_id);
      const hasGeo = !!(event.geo?.country_code && event.geo?.country_code !== 'UNK');

      // Case 1: New event
      if (!processedState) {
        processedEventIdsRef.current.set(event.event_id, { hasGeo });

        // Limit map size
        if (processedEventIdsRef.current.size > 1000) {
          const firstKey = processedEventIdsRef.current.keys().next().value;
          if (firstKey) processedEventIdsRef.current.delete(firstKey);
        }

        addAttackerNode({
          id: event.event_id,
          source_ip: event.source_ip,
          country_code: event.geo?.country_code || undefined,
          country: event.geo?.country || undefined,
          city: event.geo?.city || undefined,
          protocol: event.protocol,
          severity: event.severity,
          timestamp: event.timestamp,
          attackCount: 1,
          // Payload data for animation
          raw_data: event.raw_data,
          command: event.command,
          http_body: event.http_body,
          event_type: event.event_type,
        });
        newEventsCount++;
      }
      // Case 2: Update existing event with new Geo data
      else if (!processedState.hasGeo && hasGeo) {
        processedEventIdsRef.current.set(event.event_id, { hasGeo: true });

        // Update node directly without incrementing stats
        const nodeId = `attacker-${event.source_ip}`;
        const node = nodesRef.current.get(nodeId);
        if (node) {
          node.country_code = event.geo?.country_code || undefined;
          node.country = event.geo?.country || undefined;
          // Don't call addAttackerNode to avoid count increment
        }
      }
    });

    // Update velocity-related stats for new events only (not total, which comes from attackers)
    if (newEventsCount > 0) {
      const uniqueCountries = new Set(
        [...nodesRef.current.values()].map((n) => n.country_code).filter((cc): cc is string => !!cc)
      ).size;

      setStats((prev) => ({
        ...prev,
        countries: uniqueCountries,
        attackers: nodesRef.current.size - 1, // Subtract honeypot node
      }));
    }
  }, [events, addAttackerNode]);

  // Update visibility when activeProtocols changes
  useEffect(() => {
    // Update Nodes
    nodesRef.current.forEach((node) => {
      if (node.type === 'honeypot') {
        node.visible = true;
        return;
      }
      const isVisible =
        activeProtocols.length === 0 ||
        (node.protocol !== undefined && activeProtocols.includes(node.protocol));
      node.visible = !!isVisible;
    });

    // Update Edges
    edgesRef.current.forEach((edge) => {
      const isVisible =
        activeProtocols.length === 0 ||
        (edge.protocol !== undefined && activeProtocols.includes(edge.protocol));
      edge.visible = !!isVisible;
    });
  }, [activeProtocols]);

  // Velocity tracker
  useEffect(() => {
    const interval = setInterval(() => {
      const now = new Date();
      const recent = attackTimestampsRef.current.filter((t) => t > new Date(now.getTime() - 60000));
      setAttackVelocity(recent.length);
    }, 1000);
    return () => clearInterval(interval);
  }, []);

  return {
    nodesRef,
    edgesRef,
    heatmap: [], // Return empty heatmap as it was unused anyway after removal of fetch
    stats,
    isConnected: true, // Always true as data comes from props
    attackVelocity,
  };
};
