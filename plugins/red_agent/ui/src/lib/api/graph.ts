import { call } from './client';
import type { AttackSurfaceResp } from './types';

export const graphApi = {
  getAttackSurface: (target: string) =>
    call<AttackSurfaceResp>(`/red-agent/graph/attack-surface?target=${encodeURIComponent(target)}`),
  getFindingGraph: (findingId: string, depth: number = 2) =>
    call<AttackSurfaceResp>(
      `/red-agent/graph/finding/${encodeURIComponent(findingId)}?depth=${depth}`
    ),
};
