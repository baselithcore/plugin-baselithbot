import type { Core, NodeSingular } from 'cytoscape';
import { AttackSurfaceResp, Finding, Severity } from '../../lib/api';
import type { Selected } from '../graph/types';

export const TARGET_KEY = 'red_agent.last_target';
export const CHAT_OPEN_KEY = 'red_agent.graph_chat.open';
export const RISK_LENS_MIN_NODES = 60;

export function focusNode(cy: Core, node: NodeSingular) {
  cy.elements().removeClass('focus dim path');
  cy.elements().addClass('dim');
  node.closedNeighborhood().removeClass('dim').addClass('focus');
}

export function selectedFromNode(node: NodeSingular) {
  return {
    kind: 'node' as const,
    id: node.id(),
    label: String(node.data('label') || ''),
    display: String(node.data('display') || node.id()),
    severity: (node.data('severity') || null) as Severity | null,
    cvss: typeof node.data('cvss') === 'number' ? node.data('cvss') : null,
    neighbors: node.connectedEdges().length,
  };
}

export function clearFocus(cy: Core | null, setSelected: (s: Selected | null) => void) {
  cy?.elements().removeClass('focus dim path');
  setSelected(null);
}

export function zoomBy(cy: Core | null, factor: number) {
  if (!cy) return;
  cy.zoom({
    level: cy.zoom() * factor,
    renderedPosition: { x: cy.width() / 2, y: cy.height() / 2 },
  });
}

export function toggle<T>(set: Set<T>, v: T): Set<T> {
  const next = new Set(set);
  if (next.has(v)) next.delete(v);
  else next.add(v);
  return next;
}

export function shouldApplyRiskLens(data: AttackSurfaceResp): boolean {
  if (data.nodes.length < RISK_LENS_MIN_NODES) return false;
  return data.nodes.some((n) => n.data.severity === 'critical' || n.data.severity === 'high');
}

const SEVERITIES: ReadonlySet<Severity> = new Set(['info', 'low', 'medium', 'high', 'critical']);

export function buildStubFinding(
  id: string,
  data: AttackSurfaceResp | null,
  target: string
): Finding | null {
  const node = data?.nodes.find((n) => n.data.id === id);
  if (!node || node.data.label !== 'Vulnerability') return null;
  const sevRaw = node.data.severity;
  const severity: Severity =
    typeof sevRaw === 'string' && SEVERITIES.has(sevRaw as Severity)
      ? (sevRaw as Severity)
      : 'info';
  const cvssRaw = node.data.cvss;
  const cvss =
    typeof cvssRaw === 'number'
      ? cvssRaw
      : typeof cvssRaw === 'string' && cvssRaw !== ''
        ? Number(cvssRaw)
        : null;
  const display = node.data.display || id;
  return {
    id,
    scanner: 'unknown',
    title: display,
    description:
      'This finding is no longer present in the relational store but remains in ' +
      'the graph. Triage actions are unavailable; data shown is reconstructed ' +
      'from the attack-surface graph.',
    severity,
    cvss_score: cvss != null && Number.isFinite(cvss) ? cvss : null,
    cwe: null,
    cve: null,
    target,
    endpoint: null,
    port: null,
    service: null,
    remediation: null,
    discovered_at: '',
    state: 'open',
    assignee: null,
    triaged_at: null,
    resolved_at: null,
    due_at: null,
    notes: null,
    risk_score: null,
    controls: [],
    external_ref: null,
    evidence: { partial: true, source: 'graph_fallback' },
    raw: {},
  };
}
