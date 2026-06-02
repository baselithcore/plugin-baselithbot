import type { AttackSurfaceResp } from '../../../lib/api';
import type { FocusInfo, SuggestionGroup } from './types';

export const FALLBACK_SUGGESTIONS: SuggestionGroup[] = [
  {
    group: 'Risk',
    items: ['Top 3 findings to prioritize. Why?', 'Worst blast radius in this graph.'],
  },
  {
    group: 'Attack paths',
    items: ['Show likely attack paths.', 'Plausible lateral movement between identities.'],
  },
  {
    group: 'Coverage',
    items: ['Assets under-covered by scanners.'],
  },
];

export function buildSuggestions(
  data: AttackSurfaceResp | null,
  focus?: FocusInfo | null
): SuggestionGroup[] {
  if (!data) return FALLBACK_SUGGESTIONS;

  let criticalHigh = 0;
  let vulnerabilities = 0;
  let identities = 0;
  let scanners = 0;
  let entryPoints = 0;
  for (const n of data.nodes) {
    if (n.data.label === 'Vulnerability') vulnerabilities++;
    if (n.data.severity === 'critical' || n.data.severity === 'high') criticalHigh++;
    if (n.data.label === 'Identity') identities++;
    if (n.data.label === 'Scanner') scanners++;
    if (['Target', 'Endpoint', 'Service', 'CloudResource', 'ApiSpec'].includes(n.data.label)) {
      entryPoints++;
    }
  }
  const lateralEdges = data.edges.filter((e) => e.data.type === 'LATERAL_TO').length;
  const groups: SuggestionGroup[] = [];

  if (focus) {
    const label = compactLabel(focus.display);
    groups.push({
      group: 'Focus',
      items: [`Assess the risk around ${label}.`, `Find attack paths involving ${label}.`],
    });
  }

  groups.push({
    group: 'Risk',
    items:
      criticalHigh > 0
        ? [
            `Prioritize the top ${Math.min(3, criticalHigh)} critical/high findings.`,
            `What is the worst blast radius across ${entryPoints} entry points?`,
          ]
        : [
            `Summarize the risk posture across ${vulnerabilities} findings.`,
            'Which low-signal findings can wait?',
          ],
  });

  if (identities > 0 || lateralEdges > 0) {
    groups.push({
      group: 'Attack paths',
      items: [
        lateralEdges > 0
          ? `Explain the ${lateralEdges} lateral movement relation${lateralEdges === 1 ? '' : 's'}.`
          : `Check whether ${identities} identity node${identities === 1 ? '' : 's'} create attack paths.`,
        'Which path should an analyst validate first?',
      ],
    });
  }

  groups.push({
    group: 'Coverage',
    items: [
      scanners > 0
        ? `Which assets lack evidence from the ${scanners} scanner node${scanners === 1 ? '' : 's'}?`
        : 'Which assets look under-covered by scanners?',
    ],
  });

  return groups.slice(0, 3);
}

export function compactLabel(value: string): string {
  const trimmed = value.trim();
  if (trimmed.length <= 52) return trimmed;
  return `${trimmed.slice(0, 49)}...`;
}
