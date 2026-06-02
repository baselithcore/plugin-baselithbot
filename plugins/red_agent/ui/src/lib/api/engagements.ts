import { call, qsLoose } from './client';
import type {
  EngagementCreate,
  EngagementRecord,
  EngagementStatus,
  EngagementUpdate,
} from './types';

export const engagementsApi = {
  listEngagements: (
    filters: {
      status_filter?: EngagementStatus;
      include_archived?: boolean;
      limit?: number;
      offset?: number;
    } = {}
  ) =>
    call<EngagementRecord[]>(
      `/red-agent/engagements${qsLoose(filters as Record<string, unknown>)}`
    ),
  getEngagement: (id: string) => call<EngagementRecord>(`/red-agent/engagements/${id}`),
  createEngagement: (body: EngagementCreate) =>
    call<EngagementRecord>('/red-agent/engagements', {
      method: 'POST',
      body: JSON.stringify(body),
    }),
  updateEngagement: (id: string, body: EngagementUpdate) =>
    call<EngagementRecord>(`/red-agent/engagements/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(body),
    }),
  archiveEngagement: (id: string) =>
    call<void>(`/red-agent/engagements/${id}`, { method: 'DELETE' }),
};
