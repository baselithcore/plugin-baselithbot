/**
 * HoneypotSwarmGraph - Animated Network Graph for Honeypot Agent Activity
 *
 * Features:
 * - Heptagon layout with handlers around coordinator
 * - Animated particles flowing on attack events
 * - Node pulse effects on activity
 * - Real-time sync with logs
 */

import React, { useEffect, useRef, useState } from 'react';
import { Activity } from 'lucide-react';
import './HoneypotSwarmGraph.css';
import type { SwarmGraphProps, Particle } from './types';
import { SWARM_NODES } from './nodeConfig';
import { NodeComponent } from './NodeComponent';

const HoneypotSwarmGraph: React.FC<SwarmGraphProps> = ({ logs, stats = {}, isActive = true }) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const particlesRef = useRef<Particle[]>([]);
  const [activeNodes, setActiveNodes] = useState<Record<string, number>>({});
  const particleIdCounter = useRef(0);

  // Track isActive in a ref for use in animation loop
  const isActiveRef = useRef(isActive);
  useEffect(() => {
    isActiveRef.current = isActive;
  }, [isActive]);

  const nodes = SWARM_NODES;

  // Track last processed log timestamp
  const lastTimestampRef = useRef<string | null>(null);

  // Handle new logs and create particles
  useEffect(() => {
    if (logs.length === 0) return;

    // On first mount, just set the benchmark timestamp
    if (lastTimestampRef.current === null) {
      lastTimestampRef.current = logs[logs.length - 1].timestamp;
      return;
    }

    // Find new logs
    const newLogs = logs.filter((l) => new Date(l.timestamp) > new Date(lastTimestampRef.current!));

    if (newLogs.length === 0) return;

    // Update timestamp
    lastTimestampRef.current = newLogs[newLogs.length - 1].timestamp;

    // Helper to determine node type
    const getNodeType = (log: (typeof logs)[0]): string => {
      // 1. Specific agent_type check (most reliable)
      if (log.agent_type) {
        const type = log.agent_type.toUpperCase();
        if (type.includes('SSH')) return 'SSH';
        if (type.includes('HTTP')) return 'HTTP';
        if (type.includes('TCP')) return 'TCP';
        if (type.includes('DISCOVERY')) return 'DISCOVERY';
        if (type.includes('PENTEST')) return 'PENTEST';
        if (type.includes('CORRELAT')) return 'CORRELATOR';
        if (type.includes('RESPOND')) return 'RESPONDER';
      }

      // 2. Keyword fallback (Prioritize Complex/Specific over Generic)
      const msg = log.message.toUpperCase();

      // Priority 1: Advanced Modules (Discovery, Pentest, Correlator, AI)
      // These often mention protocols in their messages (e.g. "Discovery found SSH"),
      // so we check them FIRST to avoid false flagging as simple Handler events.
      if (
        msg.includes('DISCOVERY') ||
        msg.includes('BOTNET') ||
        msg.includes('ZERODAY') ||
        msg.includes('INTEL')
      )
        return 'DISCOVERY';

      if (msg.includes('PENTEST') || msg.includes('SCAN') || msg.includes('VULN')) return 'PENTEST';

      if (msg.includes('CVE') || msg.includes('CORRELAT')) return 'CORRELATOR';

      if (msg.includes('LLM') || msg.includes('RESPONSE') || msg.includes('RESPONDER'))
        return 'RESPONDER';

      // Priority 2: Core Protocol Handlers
      if (msg.includes('SSH')) return 'SSH';
      if (msg.includes('HTTP')) return 'HTTP';
      if (msg.includes('TCP')) return 'TCP';

      return 'OTHER';
    };

    // Process logs to create particles
    const logsToProcess: typeof logs = [];
    const processedTypes = new Set<string>();

    [...newLogs].reverse().forEach((log) => {
      const type = getNodeType(log);

      // Limit particles to avoid visual noise: max 1 per type per batch, max 5 total
      if (type !== 'OTHER' && (!processedTypes.has(type) || logsToProcess.length < 5)) {
        logsToProcess.push(log);
        processedTypes.add(type);
      }
    });

    logsToProcess.reverse().forEach((latest, index) => {
      setTimeout(() => {
        const type = getNodeType(latest);
        let startNode: keyof typeof nodes | null = null;
        let endNode: keyof typeof nodes = 'CORE';

        // Map type to start/end nodes
        switch (type) {
          case 'SSH':
            startNode = 'SSH';
            break;
          case 'HTTP':
            startNode = 'HTTP';
            break;
          case 'TCP':
            startNode = 'TCP';
            break;
          case 'DISCOVERY':
            startNode = 'CORE';
            endNode = 'DISCOVERY';
            break;
          case 'PENTEST':
            startNode = 'CORE';
            endNode = 'PENTEST';
            break;
          case 'CORRELATOR':
            startNode = 'CORE';
            endNode = 'CORRELATOR';
            break;
          case 'RESPONDER':
            startNode = 'CORE';
            endNode = 'RESPONDER';
            break;
        }

        if (startNode && containerRef.current) {
          const rect = containerRef.current.getBoundingClientRect();
          const nodeKey = startNode === 'CORE' ? endNode : startNode;

          setActiveNodes((prev) => ({ ...prev, [nodeKey]: 1 }));
          setTimeout(() => setActiveNodes((prev) => ({ ...prev, [nodeKey]: 0 })), 300);

          const pStart = nodes[startNode];
          const pEnd = nodes[endNode];
          const w = rect.width;
          const h = rect.height;

          const newParticle: Particle = {
            id: particleIdCounter.current++,
            startX: w * pStart.x,
            startY: h * pStart.y,
            targetX: w * pEnd.x,
            targetY: h * pEnd.y,
            x: w * pStart.x,
            y: h * pStart.y,
            color: pStart.color,
            progress: 0,
            speed: 0.02,
            type: startNode,
          };

          particlesRef.current.push(newParticle);
        }
      }, index * 200);
    });
  }, [logs]);

  // Animation loop
  const ambientCounterRef = useRef(0);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let animId: number;

    const animate = () => {
      // Skip heavy rendering when component is not active (tab not visible)
      if (!isActiveRef.current) {
        animId = requestAnimationFrame(animate);
        return;
      }

      ambientCounterRef.current += 0.012;
      const time = ambientCounterRef.current;

      const w = canvas.width;
      const h = canvas.height;
      if (w === 0 || h === 0) {
        animId = requestAnimationFrame(animate);
        return;
      }

      // Background (Unified with Globe tab)
      ctx.fillStyle = '#05080f';
      ctx.fillRect(0, 0, w, h);

      // Draw rectangular grid (High visibility, matching Globe tab)
      ctx.strokeStyle = 'rgba(0, 212, 255, 0.15)';
      ctx.lineWidth = 1;
      const gridSize = 50;

      for (let x = 0; x <= w; x += gridSize) {
        ctx.beginPath();
        ctx.moveTo(x, 0);
        ctx.lineTo(x, h);
        ctx.stroke();
      }
      for (let y = 0; y <= h; y += gridSize) {
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(w, y);
        ctx.stroke();
      }

      const coreX = w * nodes.CORE.x;
      const coreY = h * nodes.CORE.y;

      // Draw heptagon connections (7 nodes)
      const outerNodes = [
        'SSH',
        'HTTP',
        'DISCOVERY',
        'RESPONDER',
        'TCP',
        'PENTEST',
        'CORRELATOR',
      ] as const;

      // Outer ring (subtle)
      ctx.beginPath();
      outerNodes.forEach((key, i) => {
        const node = nodes[key];
        const nx = w * node.x;
        const ny = h * node.y;
        if (i === 0) ctx.moveTo(nx, ny);
        else ctx.lineTo(nx, ny);
      });
      ctx.closePath();
      ctx.strokeStyle = 'rgba(255, 255, 255, 0.1)';
      ctx.lineWidth = 1;
      ctx.setLineDash([2, 4]); // Dashed for technical look
      ctx.stroke();
      ctx.setLineDash([]);

      // Draw connections to core with animated gradients
      outerNodes.forEach((key) => {
        const node = nodes[key];
        const nx = w * node.x;
        const ny = h * node.y;

        const shift = (Math.sin(time * 1.5 + node.angle * 0.02) + 1) / 2;
        const grad = ctx.createLinearGradient(coreX, coreY, nx, ny);
        grad.addColorStop(0, 'rgba(255, 255, 255, 0.02)');
        grad.addColorStop(Math.max(0, shift - 0.15), 'rgba(255, 255, 255, 0.05)');
        grad.addColorStop(shift, `${node.color}aa`); // Crisp highlight
        grad.addColorStop(Math.min(1, shift + 0.15), 'rgba(255, 255, 255, 0.05)');
        grad.addColorStop(1, 'rgba(255, 255, 255, 0.02)');

        // Always visible subtle line (Structure)
        ctx.beginPath();
        ctx.moveTo(coreX, coreY);
        ctx.lineTo(nx, ny);
        ctx.strokeStyle = 'rgba(255, 255, 255, 0.03)';
        ctx.lineWidth = 1;
        ctx.stroke();

        // Active Flow (Gradient)
        ctx.beginPath();
        ctx.moveTo(coreX, coreY);
        ctx.lineTo(nx, ny);
        ctx.strokeStyle = grad;
        ctx.lineWidth = 2; // Slightly thicker for the flow
        ctx.stroke();

        // Node glow pulse
        const nodePulse = Math.sin(time * 2.5 + node.angle * 0.03) * 0.15 + 0.25;
        ctx.beginPath();
        ctx.arc(nx, ny, 30, 0, Math.PI * 2);
        const nodeGrad = ctx.createRadialGradient(nx, ny, 0, nx, ny, 30);
        nodeGrad.addColorStop(
          0,
          `${node.color}${Math.floor(nodePulse * 50)
            .toString(16)
            .padStart(2, '0')}`
        );
        nodeGrad.addColorStop(1, 'rgba(0,0,0,0)');
        ctx.fillStyle = nodeGrad;
        ctx.fill();
      });

      // Core pulsing glow
      const corePulse = Math.sin(time * 2) * 0.15 + 0.35;
      ctx.beginPath();
      ctx.arc(coreX, coreY, 40, 0, Math.PI * 2);
      const coreGrad = ctx.createRadialGradient(coreX, coreY, 0, coreX, coreY, 40);
      coreGrad.addColorStop(0, `rgba(255, 7, 58, ${corePulse})`);
      coreGrad.addColorStop(0.5, 'rgba(255, 7, 58, 0.1)');
      coreGrad.addColorStop(1, 'rgba(0,0,0,0)');
      ctx.fillStyle = coreGrad;
      ctx.fill();

      // Update and draw particles
      const currentParticles = particlesRef.current;
      const aliveParticles: Particle[] = [];

      for (const p of currentParticles) {
        p.progress += p.speed;

        if (p.progress < 1) {
          const eased = 1 - Math.pow(1 - p.progress, 3);
          p.x = p.startX + (p.targetX - p.startX) * eased;
          p.y = p.startY + (p.targetY - p.startY) * eased;

          // Glow effect
          ctx.beginPath();
          ctx.arc(p.x, p.y, 8, 0, Math.PI * 2);
          const pGlow = ctx.createRadialGradient(p.x, p.y, 0, p.x, p.y, 8);
          pGlow.addColorStop(0, p.color);
          pGlow.addColorStop(1, 'rgba(0,0,0,0)');
          ctx.fillStyle = pGlow;
          ctx.fill();

          // Core particle
          ctx.beginPath();
          ctx.arc(p.x, p.y, 3, 0, Math.PI * 2); // Smaller, crisp particle
          ctx.fillStyle = '#ffffff';
          ctx.shadowBlur = 10; // Reduced blur
          ctx.shadowColor = p.color;
          ctx.fill();
          ctx.shadowBlur = 0;

          // Trail
          const trailLen = 0.12;
          ctx.beginPath();
          ctx.moveTo(p.x, p.y);
          const prevEased = 1 - Math.pow(1 - (p.progress - trailLen), 3);
          const trailX = p.startX + (p.targetX - p.startX) * Math.max(0, prevEased);
          const trailY = p.startY + (p.targetY - p.startY) * Math.max(0, prevEased);
          ctx.lineTo(trailX, trailY);
          ctx.strokeStyle = `${p.color}80`; // Semi-transparent trail
          ctx.lineWidth = 2;
          ctx.stroke();

          aliveParticles.push(p);
        }
      }
      particlesRef.current = aliveParticles;

      animId = requestAnimationFrame(animate);
    };

    animId = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(animId);
  }, []);

  // Handle resize
  useEffect(() => {
    const handleResize = () => {
      if (containerRef.current && canvasRef.current) {
        canvasRef.current.width = containerRef.current.clientWidth;
        canvasRef.current.height = containerRef.current.clientHeight;
      }
    };
    window.addEventListener('resize', handleResize);
    handleResize();
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  return (
    <div className="swarm-graph-container" ref={containerRef}>
      <div className="swarm-graph-header">
        <Activity size={14} className="swarm-header-icon" />
        <span>HANDLER SWARM</span>
        <div className="swarm-live-badge">LIVE</div>
      </div>

      <canvas ref={canvasRef} className="swarm-canvas" />

      <NodeComponent type="SSH" data={nodes.SSH} activeNodes={activeNodes} stats={stats} />
      <NodeComponent type="HTTP" data={nodes.HTTP} activeNodes={activeNodes} stats={stats} />
      <NodeComponent
        type="DISCOVERY"
        data={nodes.DISCOVERY}
        activeNodes={activeNodes}
        stats={stats}
      />
      <NodeComponent
        type="RESPONDER"
        data={nodes.RESPONDER}
        activeNodes={activeNodes}
        stats={stats}
      />
      <NodeComponent type="TCP" data={nodes.TCP} activeNodes={activeNodes} stats={stats} />
      <NodeComponent type="PENTEST" data={nodes.PENTEST} activeNodes={activeNodes} stats={stats} />
      <NodeComponent
        type="CORRELATOR"
        data={nodes.CORRELATOR}
        activeNodes={activeNodes}
        stats={stats}
      />
      <NodeComponent type="CORE" data={nodes.CORE} activeNodes={activeNodes} stats={stats} />
    </div>
  );
};

export default React.memo(HoneypotSwarmGraph);
