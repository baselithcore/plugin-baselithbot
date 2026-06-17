import React from 'react';
import { SWARM_NODES } from './nodeConfig';

interface NodeComponentProps {
  type: string;
  data: (typeof SWARM_NODES)['CORE'];
  activeNodes: Record<string, number>;
  stats: {
    ssh_handler?: number;
    http_handler?: number;
    tcp_handler?: number;
    correlator?: number;
    responder?: number;
    pentest?: number;
    discovery?: number;
  };
}

export const NodeComponent: React.FC<NodeComponentProps> = ({ type, data, activeNodes, stats }) => {
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
