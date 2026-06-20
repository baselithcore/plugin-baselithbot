import { getToken } from '../../lib/api';

export type ReachabilitySeverity = 'info' | 'low' | 'medium' | 'high';
export type WebhookMinSeverity = 'info' | 'low' | 'medium' | 'high' | 'critical';

export interface ScopeResp {
  scope_allowlist: string[];
  bug_bounty_mode: boolean;
  bug_bounty_program_id: string | null;
  allow_internal_targets: boolean;
  require_hitl_for_active: boolean;
  max_concurrent_scans: number;
  enabled_scanners: string[];
  scanner_timeouts: Record<string, number>;
  audit_retention_days: number;
  sandbox_provider: string;
  graph_backend: string;
  multi_step_chains: boolean;
  chain_max_iterations: number;
  validated_impact_only: boolean;
  validated_impact_min_cvss: number;
  epss_kev_enricher_enabled: boolean;
  epss_kev_bump_severity_on_kev: boolean;
  epss_kev_high_epss_threshold: number;
  attack_mapper_enabled: boolean;
  osv_enricher_enabled: boolean;
  greynoise_enricher_enabled: boolean;
  reachability_enabled: boolean;
  reachability_drop_unreachable: boolean;
  reachability_drop_max_severity: ReachabilitySeverity;
  vex_enabled: boolean;
  vex_suppress_not_affected: boolean;
  vex_suppress_fixed: boolean;
  risk_scoring_enabled: boolean;
  compliance_mapper_enabled: boolean;
  differential_enabled: boolean;
  differential_ttl_seconds: number;
  auto_remediation_enabled: boolean;
  webhook_enabled: boolean;
  webhook_url_configured: boolean;
  webhook_min_severity: WebhookMinSeverity;
  webhook_in_enabled: boolean;
  webhook_in_require_signature: boolean;
  webhook_replay_protection: boolean;
  editable_fields: string[];
  allowed_scanners: string[];
}

export type Update = Partial<
  Omit<
    ScopeResp,
    | 'sandbox_provider'
    | 'graph_backend'
    | 'editable_fields'
    | 'allowed_scanners'
    | 'webhook_url_configured'
  >
>;

const authHeaders = (): HeadersInit => ({
  'Content-Type': 'application/json',
  Authorization: `Bearer ${getToken()}`,
});

export async function fetchScope(): Promise<ScopeResp> {
  const r = await fetch('/red-agent/settings/scope', { headers: authHeaders() });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function saveScope(payload: Update): Promise<ScopeResp> {
  const r = await fetch('/red-agent/settings/scope', {
    method: 'PUT',
    headers: authHeaders(),
    body: JSON.stringify(payload),
  });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export function diff(base: ScopeResp, next: ScopeResp): Update {
  const out: Record<string, unknown> = {};
  const keys: (keyof ScopeResp)[] = [
    'scope_allowlist',
    'bug_bounty_mode',
    'bug_bounty_program_id',
    'allow_internal_targets',
    'require_hitl_for_active',
    'max_concurrent_scans',
    'audit_retention_days',
    'enabled_scanners',
    'scanner_timeouts',
    'multi_step_chains',
    'chain_max_iterations',
    'validated_impact_only',
    'validated_impact_min_cvss',
    'epss_kev_enricher_enabled',
    'epss_kev_bump_severity_on_kev',
    'epss_kev_high_epss_threshold',
    'attack_mapper_enabled',
    'osv_enricher_enabled',
    'greynoise_enricher_enabled',
    'reachability_enabled',
    'reachability_drop_unreachable',
    'reachability_drop_max_severity',
    'vex_enabled',
    'vex_suppress_not_affected',
    'vex_suppress_fixed',
    'risk_scoring_enabled',
    'compliance_mapper_enabled',
    'differential_enabled',
    'differential_ttl_seconds',
    'auto_remediation_enabled',
    'webhook_enabled',
    'webhook_min_severity',
    'webhook_in_enabled',
    'webhook_in_require_signature',
    'webhook_replay_protection',
  ];
  for (const k of keys) {
    if (JSON.stringify(base[k]) !== JSON.stringify(next[k])) {
      out[k] = next[k];
    }
  }
  return out as Update;
}
