export interface SwarmGraphProps {
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

export interface Particle {
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
