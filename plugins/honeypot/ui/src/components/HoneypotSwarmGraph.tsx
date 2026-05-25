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
import {
  Activity,
  Terminal,
  Globe,
  Radio,
  Link2,
  Bot,
  Hexagon,
  Shield,
  Search,
} from 'lucide-react';
import './HoneypotSwarmGraph.css';

interface SwarmGraphProps {
  logs: Array<{
    timestamp: string;
    message: string;
    is_alert: boolean;
    is_error: boolean;
    agent_type?: string;
  }>;
  stats?: {
    ssh_handler?: number;
    http_handler?: number;
    tcp_handler?: number;
    correlator?: number;
    responder?: number;
    pentest?: number;
    discovery?: number;
  };
  /** When false, animation loop is paused to save CPU */
  isActive?: boolean;
}

interface Particle {
  id: number;
  startX: number;
  startY: number;
  targetX: number;
  targetY: number;
  x: number;
  y: number;
  color: string;
  progress: number;
  speed: number;
  type: string;
}

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

  // Heptagon Layout: 7 handler nodes around coordinator
  // Using radius 0.35 from center (0.5, 0.5) for better spacing
  // Angles: 360/7 ≈ 51.43° between each node, starting from top

  const nodes = {
    SSH: {
      x: 0.5, // Top center
      y: 0.15,
      color: '#00ff88',
      label: 'SSH Handler',
      icon: Terminal,
      angle: -90,
    },
    HTTP: {
      x: 0.78, // Top right
      y: 0.27,
      color: '#00d4ff',
      label: 'HTTP Handler',
      icon: Globe,
      angle: -38,
    },
    DISCOVERY: {
      x: 0.85, // Right
      y: 0.58,
      color: '#ff6b9d',
      label: 'Discovery',
      icon: Search,
      angle: 13,
    },
    RESPONDER: {
      x: 0.65, // Bottom right
      y: 0.82,
      color: '#9d4edd',
      label: 'LLM Responder',
      icon: Bot,
      angle: 64,
    },
    TCP: {
      x: 0.35, // Bottom left
      y: 0.82,
      color: '#ff6b35',
      label: 'TCP Handler',
      icon: Radio,
      angle: 116,
    },
    PENTEST: {
      x: 0.15, // Left
      y: 0.58,
      color: '#00ff9d',
      label: 'Pentest',
      icon: Shield,
      angle: 167,
    },
    CORRELATOR: {
      x: 0.22, // Top left
      y: 0.27,
      color: '#ffbe0b',
      label: 'CVE Correlator',
      icon: Link2,
      angle: 218,
    },
    CORE: {
      x: 0.5,
      y: 0.5,
      color: '#ff073a',
      label: 'Coordinator',
      icon: Hexagon,
      angle: 0,
    },
  };

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

  const NodeComponent = ({ type, data }: { type: string; data: (typeof nodes)['CORE'] }) => {
    const isActive = activeNodes[type] === 1;
    const statKey = type.toLowerCase().replace(' ', '_') as keyof typeof stats;
    const taskCount = stats?.[statKey] ?? 0;
    const IconComponent = data.icon;

    return (
      <div
        className={`swarm-node ${isActive ? 'active' : ''}`}
        style={{
          left: `${data.x * 100}%`,
          top: `${data.y * 100}%`,
        }}
      >
        <div
          className="swarm-node-icon"
          style={{
            borderColor: isActive ? '#fff' : data.color,
            boxShadow: isActive
              ? `0 0 25px ${data.color}, 0 0 50px ${data.color}40, inset 0 0 15px ${data.color}40`
              : `0 0 15px ${data.color}30`,
            transform: isActive ? 'scale(1.15)' : 'scale(1)',
          }}
        >
          <IconComponent size={type === 'CORE' ? 24 : 18} color={isActive ? '#fff' : data.color} />
          {taskCount > 0 && type !== 'CORE' && (
            <span className="swarm-node-badge" style={{ background: data.color }}>
              {taskCount}
            </span>
          )}
        </div>
        <span
          className="swarm-node-label"
          style={{
            color: isActive ? '#fff' : 'rgba(255,255,255,0.8)',
            textShadow: `0 0 8px ${data.color}50`,
          }}
        >
          {data.label}
        </span>
      </div>
    );
  };

  return (
    <div className="swarm-graph-container" ref={containerRef}>
      <div className="swarm-graph-header">
        <Activity size={14} className="swarm-header-icon" />
        <span>HANDLER SWARM</span>
        <div className="swarm-live-badge">LIVE</div>
      </div>

      <canvas ref={canvasRef} className="swarm-canvas" />

      <NodeComponent type="SSH" data={nodes.SSH} />
      <NodeComponent type="HTTP" data={nodes.HTTP} />
      <NodeComponent type="DISCOVERY" data={nodes.DISCOVERY} />
      <NodeComponent type="RESPONDER" data={nodes.RESPONDER} />
      <NodeComponent type="TCP" data={nodes.TCP} />
      <NodeComponent type="PENTEST" data={nodes.PENTEST} />
      <NodeComponent type="CORRELATOR" data={nodes.CORRELATOR} />
      <NodeComponent type="CORE" data={nodes.CORE} />
    </div>
  );
};

export default React.memo(HoneypotSwarmGraph);
