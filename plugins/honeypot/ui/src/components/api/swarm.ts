/**
 * Swarm Status APIs
 * Monitoring and status for honeypot swarm handlers
 */

import { honeypotApiFetch } from './core';

export interface SwarmHandler {
  active: boolean;
  events: number;
  sessions: number;
}

export interface SwarmStatusResponse {
  handlers: Record<string, SwarmHandler>;
  total_events: number;
  active_sessions: number;
  is_running: boolean;
}

export async function fetchSwarmStatus(): Promise<SwarmStatusResponse> {
  return honeypotApiFetch<SwarmStatusResponse>('/swarm/status');
}
