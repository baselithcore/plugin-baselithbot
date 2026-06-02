import { call, qsLoose } from './client';
import type {
  AgentDetail,
  AgentOS,
  AgentStatus,
  AgentSummary,
  AgentTelemetryRow,
  EnrollmentTokenIssued,
} from './types';

export const fleetApi = {
  // ── Fleet (endpoint daemons) ──────────────────────────────────────
  listFleet: (
    filters: {
      status_filter?: AgentStatus;
      os?: AgentOS;
      limit?: number;
      offset?: number;
    } = {}
  ) => call<AgentSummary[]>(`/red-agent/agents${qsLoose(filters as Record<string, unknown>)}`),
  getAgent: (uuid: string) => call<AgentDetail>(`/red-agent/agents/${uuid}`),
  listAgentTelemetry: (uuid: string, opts: { kind?: string; limit?: number } = {}) =>
    call<AgentTelemetryRow[]>(
      `/red-agent/agents/${uuid}/telemetry${qsLoose(opts as Record<string, unknown>)}`
    ),
  listFleetTelemetry: (opts: { kind?: string; limit?: number } = {}) =>
    call<AgentTelemetryRow[]>(
      `/red-agent/agents/telemetry${qsLoose(opts as Record<string, unknown>)}`
    ),
  createEnrollmentToken: (body: {
    ttl_seconds?: number;
    bind_agent_uuid?: string;
    labels?: Record<string, unknown>;
  }) =>
    call<EnrollmentTokenIssued>('/red-agent/agents/enrollment-tokens', {
      method: 'POST',
      body: JSON.stringify(body),
    }),
};
