import React, { useEffect, useRef, useState } from 'react';
import { Activity, Zap, Search, Globe, Hexagon, GitBranch, FileText } from 'lucide-react';

interface DiscoveryNetworkProps {
  logs: Array<{ timestamp: string; message: string; is_alert: boolean; is_error: boolean }>;
  stats?: {
    scanner?: number;
    analyzer?: number;
    discovery?: number;
    correlator?: number;
    reporter?: number;
  };
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

const DiscoveryNetwork: React.FC<DiscoveryNetworkProps> = ({ logs, stats = {} }) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);

  const particlesRef = useRef<Particle[]>([]);
  const [activeNodes, setActiveNodes] = useState<Record<string, number>>({});
  const particleIdCounter = useRef(0);

  // Pentagon Layout: 5 nodes around center
  const nodes = {
    SCANNER: { x: 0.5, y: 0.12, color: '#00ff88', label: 'Scanner', icon: Search, angle: -90 },
    ANALYZER: { x: 0.88, y: 0.38, color: '#00f5ff', label: 'Analyzer', icon: Zap, angle: -18 },
    REPORTER: { x: 0.73, y: 0.85, color: '#9d4edd', label: 'Reporter', icon: FileText, angle: 54 },
    DISCOVERY: { x: 0.27, y: 0.85, color: '#ff0080', label: 'Discovery', icon: Globe, angle: 126 },
    CORRELATOR: {
      x: 0.12,
      y: 0.38,
      color: '#ffbe0b',
      label: 'Correlator',
      icon: GitBranch,
      angle: 198,
    },
    CORE: { x: 0.5, y: 0.48, color: '#ffffff', label: 'Coordinator', icon: Hexagon, angle: 0 },
  };

  // Handle New Logs & Create Particles
  const lastTimestampRef = useRef<string | null>(null);

  useEffect(() => {
    if (logs.length === 0) return;

    // On first mount, just set the benchmark timestamp without exploding particles
    if (lastTimestampRef.current === null) {
      lastTimestampRef.current = logs[logs.length - 1].timestamp;
      return;
    }

    // Identify ALL new logs since last render
    const newLogs = logs.filter((l) => new Date(l.timestamp) > new Date(lastTimestampRef.current!));

    if (newLogs.length === 0) return;

    // Update timestamp to the newest one
    lastTimestampRef.current = newLogs[newLogs.length - 1].timestamp;

    // Smart Batching: Ensure we show animation for ALL active agent types
    const logsToProcess: typeof logs = [];
    const processedTypes = new Set<string>();

    // Process from newest to oldest to prioritize latest activity per agent
    [...newLogs].reverse().forEach((log) => {
      let type = 'OTHER';
      const msg = log.message.toUpperCase();
      if (msg.includes('SCANNER')) type = 'SCANNER';
      else if (msg.includes('DISCOVERY')) type = 'DISCOVERY';
      else if (msg.includes('CORRELAT')) type = 'CORRELATOR';
      else if (msg.includes('REPORT')) type = 'REPORTER';
      else if (msg.includes('ANALYZER')) type = 'ANALYZER';

      // Always include if we haven't seen this agent type yet in this batch
      // Or if we have space (up to limit)
      if (!processedTypes.has(type) || logsToProcess.length < 5) {
        logsToProcess.push(log);
        processedTypes.add(type);
      }
    });

    // Reverse back to chronological order for animation
    logsToProcess.reverse().forEach((latest, index) => {
      // Stagger animations slightly for batch updates
      setTimeout(() => {
        const msg = latest.message.toUpperCase();
        let startNode: keyof typeof nodes | null = null;
        let endNode: keyof typeof nodes | null = 'CORE';

        if (msg.includes('SCANNER')) startNode = 'SCANNER';
        else if (msg.includes('DISCOVERY')) startNode = 'DISCOVERY';
        else if (msg.includes('CORRELAT')) startNode = 'CORRELATOR';
        else if (msg.includes('REPORT')) startNode = 'REPORTER';
        else if (msg.includes('ANALYZER')) {
          if (msg.includes('STARTING')) {
            startNode = 'CORE';
            endNode = 'ANALYZER';
          } else {
            startNode = 'ANALYZER';
            endNode = 'CORE';
          }
        }

        if (startNode && endNode && containerRef.current) {
          const rect = containerRef.current.getBoundingClientRect();
          const nodeKey = startNode;

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
            speed: 0.02, // Slightly slower for better visibility
            type: startNode,
          };

          particlesRef.current.push(newParticle);
        }
      }, index * 250); // Increased stagger for distinct pulses
    });
  }, [logs]);

  // Animation Loop
  const ambientCounterRef = useRef(0);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let animId: number;

    const animate = () => {
      ambientCounterRef.current += 0.012;
      const time = ambientCounterRef.current;

      const w = canvas.width;
      const h = canvas.height;
      if (w === 0 || h === 0) {
        animId = requestAnimationFrame(animate);
        return;
      }

      // Deep space background with gradient
      const bgGrad = ctx.createRadialGradient(w / 2, h / 2, 0, w / 2, h / 2, w * 0.7);
      bgGrad.addColorStop(0, '#0f0f1a');
      bgGrad.addColorStop(1, '#050508');
      ctx.fillStyle = bgGrad;
      ctx.fillRect(0, 0, w, h);

      // Animated hex grid
      const gridPulse = Math.sin(time * 0.3) * 0.03 + 0.08;
      ctx.strokeStyle = `rgba(0, 255, 136, ${gridPulse})`;
      ctx.lineWidth = 0.5;
      const gridSize = 35;
      for (let x = 0; x < w; x += gridSize) {
        ctx.beginPath();
        ctx.moveTo(x, 0);
        ctx.lineTo(x, h);
        ctx.stroke();
      }
      for (let y = 0; y < h; y += gridSize) {
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(w, y);
        ctx.stroke();
      }

      const coreX = w * nodes.CORE.x;
      const coreY = h * nodes.CORE.y;

      // Draw pentagon connections between outer nodes
      const outerNodes = ['SCANNER', 'ANALYZER', 'REPORTER', 'DISCOVERY', 'CORRELATOR'] as const;

      // Pentagon outer ring (subtle)
      ctx.beginPath();
      outerNodes.forEach((key, i) => {
        const node = nodes[key];
        const nx = w * node.x;
        const ny = h * node.y;
        if (i === 0) ctx.moveTo(nx, ny);
        else ctx.lineTo(nx, ny);
      });
      ctx.closePath();
      ctx.strokeStyle = 'rgba(255, 255, 255, 0.05)';
      ctx.lineWidth = 1;
      ctx.stroke();

      // Draw connections to core with animated gradients
      outerNodes.forEach((key) => {
        const node = nodes[key];
        const nx = w * node.x;
        const ny = h * node.y;

        const shift = (Math.sin(time * 1.5 + node.angle * 0.02) + 1) / 2;
        const grad = ctx.createLinearGradient(coreX, coreY, nx, ny);
        grad.addColorStop(0, 'rgba(255, 255, 255, 0.03)');
        grad.addColorStop(Math.max(0, shift - 0.15), 'rgba(255, 255, 255, 0.06)');
        grad.addColorStop(shift, `${node.color}50`);
        grad.addColorStop(Math.min(1, shift + 0.15), 'rgba(255, 255, 255, 0.06)');
        grad.addColorStop(1, 'rgba(255, 255, 255, 0.03)');

        ctx.beginPath();
        ctx.moveTo(coreX, coreY);
        ctx.lineTo(nx, ny);
        ctx.strokeStyle = grad;
        ctx.lineWidth = 2;
        ctx.stroke();

        // Node glow pulse
        const nodePulse = Math.sin(time * 2.5 + node.angle * 0.03) * 0.15 + 0.25;
        ctx.beginPath();
        ctx.arc(nx, ny, 35, 0, Math.PI * 2);
        const nodeGrad = ctx.createRadialGradient(nx, ny, 0, nx, ny, 35);
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
      const corePulse = Math.sin(time * 2) * 0.1 + 0.3;
      ctx.beginPath();
      ctx.arc(coreX, coreY, 45, 0, Math.PI * 2);
      const coreGrad = ctx.createRadialGradient(coreX, coreY, 0, coreX, coreY, 45);
      coreGrad.addColorStop(0, `rgba(255, 255, 255, ${corePulse})`);
      coreGrad.addColorStop(0.5, 'rgba(0, 255, 136, 0.1)');
      coreGrad.addColorStop(1, 'rgba(0,0,0,0)');
      ctx.fillStyle = coreGrad;
      ctx.fill();

      // Update and Draw Particles
      const currentParticles = particlesRef.current;
      const aliveParticles: Particle[] = [];

      for (let i = 0; i < currentParticles.length; i++) {
        const p = currentParticles[i];
        p.progress += p.speed;

        if (p.progress < 1) {
          // Smooth easing
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
          ctx.arc(p.x, p.y, 3, 0, Math.PI * 2);
          ctx.fillStyle = '#ffffff';
          ctx.shadowBlur = 10;
          ctx.shadowColor = p.color;
          ctx.fill();
          ctx.shadowBlur = 0;

          // Trail
          const trailLen = 0.08;
          ctx.beginPath();
          ctx.moveTo(p.x, p.y);
          const prevEased = 1 - Math.pow(1 - (p.progress - trailLen), 3);
          const trailX = p.startX + (p.targetX - p.startX) * Math.max(0, prevEased);
          const trailY = p.startY + (p.targetY - p.startY) * Math.max(0, prevEased);
          ctx.lineTo(trailX, trailY);
          ctx.strokeStyle = `${p.color}80`;
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

  // Handle Resize
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
    const taskCount = stats?.[type.toLowerCase() as keyof typeof stats] ?? 0;

    return (
      <div
        style={{
          position: 'absolute',
          left: `${data.x * 100}%`,
          top: `${data.y * 100}%`,
          transform: 'translate(-50%, -50%)',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          zIndex: 10,
          transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
        }}
      >
        <div
          style={{
            width: type === 'CORE' ? '56px' : '44px',
            height: type === 'CORE' ? '56px' : '44px',
            borderRadius: type === 'CORE' ? '16px' : '12px',
            backgroundColor: 'rgba(10, 10, 20, 0.9)',
            border: `2px solid ${isActive ? '#fff' : data.color}`,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: isActive
              ? `0 0 25px ${data.color}, 0 0 50px ${data.color}40, inset 0 0 15px ${data.color}40`
              : `0 0 15px ${data.color}30`,
            transform: isActive ? 'scale(1.15)' : 'scale(1)',
            transition: 'all 0.2s cubic-bezier(0.175, 0.885, 0.32, 1.275)',
            backdropFilter: 'blur(10px)',
            position: 'relative',
          }}
        >
          <data.icon size={type === 'CORE' ? 26 : 20} color={isActive ? '#fff' : data.color} />
          {taskCount > 0 && type !== 'CORE' && (
            <span
              style={{
                position: 'absolute',
                top: '-6px',
                right: '-6px',
                background: data.color,
                color: '#000',
                fontSize: '9px',
                fontWeight: 'bold',
                padding: '2px 5px',
                borderRadius: '8px',
                minWidth: '16px',
                textAlign: 'center',
              }}
            >
              {taskCount}
            </span>
          )}
        </div>
        <span
          style={{
            marginTop: '6px',
            fontSize: '10px',
            color: isActive ? '#fff' : 'rgba(255,255,255,0.8)',
            fontFamily: "'JetBrains Mono', monospace",
            letterSpacing: '0.5px',
            textShadow: `0 0 8px ${data.color}50`,
            fontWeight: 600,
            whiteSpace: 'nowrap',
            textTransform: 'uppercase',
          }}
        >
          {data.label}
        </span>
      </div>
    );
  };

  return (
    <div
      className="cyber-card"
      style={{
        height: '340px',
        marginBottom: '20px',
        overflow: 'hidden',
        position: 'relative',
        background: 'linear-gradient(135deg, #0a0a12 0%, #050508 100%)',
        border: '1px solid rgba(0, 255, 136, 0.2)',
        borderRadius: '16px',
      }}
      ref={containerRef}
    >
      <h2
        style={{
          position: 'absolute',
          top: '16px',
          left: '20px',
          fontSize: '11px',
          opacity: 0.9,
          color: '#fff',
          letterSpacing: '2px',
          fontWeight: 600,
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          zIndex: 20,
        }}
      >
        <Activity size={14} style={{ color: 'var(--cyber-neon-green)' }} />
        SWARM NETWORK
        <span
          style={{
            background: 'rgba(0, 255, 136, 0.15)',
            border: '1px solid rgba(0, 255, 136, 0.3)',
            padding: '2px 8px',
            borderRadius: '4px',
            fontSize: '9px',
            color: 'var(--cyber-neon-green)',
          }}
        >
          LIVE
        </span>
      </h2>

      <canvas
        ref={canvasRef}
        style={{ width: '100%', height: '100%', position: 'absolute', top: 0, left: 0 }}
      />

      <NodeComponent type="SCANNER" data={nodes.SCANNER} />
      <NodeComponent type="ANALYZER" data={nodes.ANALYZER} />
      <NodeComponent type="REPORTER" data={nodes.REPORTER} />
      <NodeComponent type="DISCOVERY" data={nodes.DISCOVERY} />
      <NodeComponent type="CORRELATOR" data={nodes.CORRELATOR} />
      <NodeComponent type="CORE" data={nodes.CORE} />
    </div>
  );
};

export default React.memo(DiscoveryNetwork);
