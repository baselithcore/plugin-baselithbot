import { AttackSurfaceResp, Severity } from '../../lib/api';
import { severityRank } from '../graph/styles';
import type { Counts } from '../graph/Toolbar';
import type { GraphSummaryStats, NodeType } from '../graph/types';

export function computeCounts(
  data: AttackSurfaceResp | null,
  severities: Set<Severity>,
  types: Set<NodeType>
): Counts {
  if (!data) return { nodes: 0, edges: 0, critical: 0, high: 0, hidden: 0 };
  let critical = 0;
  let high = 0;
  for (const n of data.nodes) {
    if (n.data.severity === 'critical') critical++;
    else if (n.data.severity === 'high') high++;
  }
  let hidden = 0;
  if (severities.size > 0 || types.size > 0) {
    for (const n of data.nodes) {
      const lbl = n.data.label as NodeType;
      if (types.size > 0 && !types.has(lbl)) hidden++;
      else if (severities.size > 0 && n.data.severity && !severities.has(n.data.severity)) hidden++;
    }
  }
  return { nodes: data.nodes.length, edges: data.edges.length, critical, high, hidden };
}

export function computeSortedNodes(data: AttackSurfaceResp | null) {
  if (!data) return [];
  return [...data.nodes].sort(
    (a, b) => severityRank(b.data.severity) - severityRank(a.data.severity)
  );
}

export function computeSummaryStats(
  data: AttackSurfaceResp | null,
  hiddenCount: number
): GraphSummaryStats | null {
  if (!data) return null;
  let vulnerabilities = 0;
  let criticalHigh = 0;
  let entryPoints = 0;
  let enrichments = 0;
  let maxCvss: number | null = null;

  for (const n of data.nodes) {
    if (n.data.label === 'Vulnerability') vulnerabilities++;
    if (n.data.severity === 'critical' || n.data.severity === 'high') criticalHigh++;
    if (['Target', 'Endpoint', 'Service', 'CloudResource', 'ApiSpec'].includes(n.data.label)) {
      entryPoints++;
    }
    if (typeof n.data.cvss === 'number') maxCvss = Math.max(maxCvss ?? 0, n.data.cvss);
  }
  for (const e of data.edges) {
    if (['MAPS_TO', 'DETECTED_BY', 'GOVERNED_BY', 'RUNS_AS', 'STORES'].includes(e.data.type)) {
      enrichments++;
    }
  }
  const exposureScore = Math.min(
    100,
    Math.round(
      criticalHigh * 18 +
        Math.max(0, vulnerabilities - criticalHigh) * 5 +
        entryPoints * 2 +
        (maxCvss ?? 0) * 3
    )
  );
  return {
    nodes: data.nodes.length,
    edges: data.edges.length,
    visibleNodes: Math.max(0, data.nodes.length - hiddenCount),
    vulnerabilities,
    criticalHigh,
    entryPoints,
    enrichments,
    maxCvss,
    exposureScore,
  };
}
