import { useEffect, useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Button, Card, Chip, EmptyState, Icon, PageHeader } from '../components/ui';
import { type ScopeResp, diff, fetchScope, saveScope } from './scope_policy/_api';
import { AllowlistEditor } from './scope_policy/AllowlistEditor';
import { NumberInput, NumberRow, Row, SelectInput, ToggleRow } from './scope_policy/form_controls';
import { ScannerGrid } from './scope_policy/ScannerGrid';

export function ScopePolicy() {
  const qc = useQueryClient();
  const { data, isLoading, error } = useQuery({ queryKey: ['scope'], queryFn: fetchScope });
  const [draft, setDraft] = useState<ScopeResp | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);

  useEffect(() => {
    if (data) setDraft(data);
  }, [data]);

  const mutation = useMutation({
    mutationFn: saveScope,
    onSuccess: (next) => {
      setDraft(next);
      setSaveError(null);
      qc.setQueryData(['scope'], next);
    },
    onError: (err: Error) => setSaveError(err.message || 'Save failed'),
  });

  const dirty = useMemo(() => {
    if (!data || !draft) return false;
    return JSON.stringify(diff(data, draft)) !== '{}';
  }, [data, draft]);

  if (isLoading) {
    return (
      <div className="grid place-items-center py-20 text-sm text-text-muted">
        <span className="font-mono">Loading scope policy…</span>
      </div>
    );
  }
  if (error) {
    return (
      <div className="rounded border border-sev-critical/40 bg-sev-critical/10 p-3 text-sm text-sev-critical">
        {String(error)}
      </div>
    );
  }
  if (!data || !draft) return null;

  const update = <K extends keyof ScopeResp>(key: K, value: ScopeResp[K]) =>
    setDraft((d) => (d ? { ...d, [key]: value } : d));

  const onSave = () => {
    const payload = diff(data, draft);
    if (Object.keys(payload).length === 0) return;
    mutation.mutate(payload);
  };

  const onReset = () => {
    setDraft(data);
    setSaveError(null);
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Scope & Policy"
        description="Editable runtime policy. Env vars (RED_AGENT_*) seed defaults; changes here persist as overrides."
        breadcrumbs={[{ label: 'Configuration' }, { label: 'Scope & Policy' }]}
        meta={
          <div className="flex flex-wrap gap-1.5">
            <Chip tone={draft.bug_bounty_mode ? 'warn' : 'neutral'}>
              <Icon.Shield size={11} />
              bug-bounty {draft.bug_bounty_mode ? 'on' : 'off'}
            </Chip>
            <Chip tone={draft.allow_internal_targets ? 'critical' : 'neutral'}>
              {draft.allow_internal_targets
                ? 'internal targets allowed'
                : 'internal targets blocked'}
            </Chip>
            <Chip tone={draft.require_hitl_for_active ? 'good' : 'warn'}>
              HITL on active: {draft.require_hitl_for_active ? 'yes' : 'no'}
            </Chip>
          </div>
        }
        actions={
          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              size="sm"
              onClick={onReset}
              disabled={!dirty || mutation.isPending}
            >
              Reset
            </Button>
            <Button
              variant="primary"
              size="sm"
              onClick={onSave}
              disabled={!dirty || mutation.isPending}
            >
              <Icon.Save size={12} />
              {mutation.isPending ? 'Saving…' : 'Save'}
            </Button>
          </div>
        }
      />

      {saveError && (
        <div className="rounded border border-sev-critical/40 bg-sev-critical/10 p-3 text-sm text-sev-critical">
          {saveError}
        </div>
      )}

      <div className="grid gap-4 lg:grid-cols-3">
        <Card
          className="lg:col-span-2"
          title="Scope allowlist"
          subtitle={`${draft.scope_allowlist.length} entries`}
        >
          <AllowlistEditor
            entries={draft.scope_allowlist}
            onChange={(entries) => update('scope_allowlist', entries)}
          />
        </Card>

        <Card title="Engine" subtitle="Runtime configuration">
          <dl className="space-y-3 text-sm">
            <NumberRow
              label="Max concurrent scans"
              value={draft.max_concurrent_scans}
              min={1}
              max={64}
              onChange={(v) => update('max_concurrent_scans', v)}
            />
            <NumberRow
              label="Audit retention (days)"
              value={draft.audit_retention_days}
              min={1}
              max={3650}
              onChange={(v) => update('audit_retention_days', v)}
            />
            <Row label="Sandbox provider" value={draft.sandbox_provider} />
            <Row label="Graph backend" value={draft.graph_backend} />
          </dl>
        </Card>
      </div>

      <Card title="Policy switches" subtitle="Bug-bounty, HITL, internal targets">
        <div className="grid gap-4 sm:grid-cols-2">
          <ToggleRow
            label="Bug-bounty mode"
            description="Bypass scope allowlist; rely on upstream program."
            checked={draft.bug_bounty_mode}
            onChange={(v) => update('bug_bounty_mode', v)}
          />
          <ToggleRow
            label="Require HITL for active scans"
            description="Active/intrusive scans wait for human approval."
            checked={draft.require_hitl_for_active}
            onChange={(v) => update('require_hitl_for_active', v)}
          />
          <ToggleRow
            label="Allow internal targets"
            description="Override SSRF guard for loopback/private/link-local."
            checked={draft.allow_internal_targets}
            tone="danger"
            onChange={(v) => update('allow_internal_targets', v)}
          />
          <ToggleRow
            label="Multi-step attack chains"
            description="Recon-first, then DAST against discovered endpoints."
            checked={draft.multi_step_chains}
            onChange={(v) => update('multi_step_chains', v)}
          />
        </div>

        <div className="mt-5 grid gap-4 sm:grid-cols-2">
          <div>
            <label className="mb-1.5 block text-2xs font-mono uppercase tracking-wider text-text-muted">
              Bug-bounty program ID
            </label>
            <input
              type="text"
              value={draft.bug_bounty_program_id ?? ''}
              onChange={(e) => update('bug_bounty_program_id', e.target.value.trim() || null)}
              placeholder="hackerone:program-handle"
              className="ra-input"
              disabled={!draft.bug_bounty_mode}
            />
          </div>
          <NumberInput
            label="Chain max iterations"
            value={draft.chain_max_iterations}
            min={1}
            max={20}
            onChange={(v) => update('chain_max_iterations', v)}
          />
        </div>
      </Card>

      <Card
        title="Enabled scanners"
        subtitle={`${draft.enabled_scanners.length} of ${draft.allowed_scanners.length} active`}
        action={
          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => update('enabled_scanners', draft.allowed_scanners.slice())}
            >
              All
            </Button>
            <Button variant="ghost" size="sm" onClick={() => update('enabled_scanners', [])}>
              None
            </Button>
          </div>
        }
      >
        <ScannerGrid
          allowed={draft.allowed_scanners}
          enabled={draft.enabled_scanners}
          onToggle={(name, on) =>
            update(
              'enabled_scanners',
              on
                ? Array.from(new Set([...draft.enabled_scanners, name]))
                : draft.enabled_scanners.filter((x) => x !== name)
            )
          }
        />
        {draft.enabled_scanners.length === 0 && (
          <EmptyState
            compact
            icon={<Icon.Target size={20} />}
            title="No scanners enabled"
            description="Pick at least one to allow scans."
          />
        )}
      </Card>

      <Card title="Threat-intel enrichment" subtitle="EPSS · CISA KEV · MITRE ATT&CK mapping">
        <div className="grid gap-4 sm:grid-cols-2">
          <ToggleRow
            label="EPSS + CISA KEV enricher"
            description="Annotate CVE-bearing findings with FIRST EPSS scores and KEV listing. Fail-open."
            checked={draft.epss_kev_enricher_enabled}
            onChange={(v) => update('epss_kev_enricher_enabled', v)}
          />
          <ToggleRow
            label="Bump severity on KEV"
            description="Findings whose CVE is on the CISA KEV catalog are bumped to HIGH (if currently lower)."
            checked={draft.epss_kev_bump_severity_on_kev}
            onChange={(v) => update('epss_kev_bump_severity_on_kev', v)}
          />
          <NumberInput
            label="High EPSS threshold (0–1)"
            value={draft.epss_kev_high_epss_threshold}
            min={0}
            max={1}
            step={0.05}
            onChange={(v) => update('epss_kev_high_epss_threshold', v)}
          />
          <ToggleRow
            label="MITRE ATT&CK mapper"
            description="Annotate findings with ATT&CK technique IDs derived from CWE. Pure local lookup."
            checked={draft.attack_mapper_enabled}
            onChange={(v) => update('attack_mapper_enabled', v)}
          />
        </div>
      </Card>

      <Card
        title="Risk & compliance"
        subtitle="VPR-style scoring · CIS / PCI / NIST / ISO / SOC 2 mapping"
      >
        <div className="grid gap-4 sm:grid-cols-2">
          <ToggleRow
            label="Unified risk score"
            description="Compute VPR-style 0–10 risk per finding from CVSS + EPSS + KEV + reachability + asset criticality."
            checked={draft.risk_scoring_enabled}
            onChange={(v) => update('risk_scoring_enabled', v)}
          />
          <ToggleRow
            label="Compliance mapper"
            description="Annotate findings with CIS / PCI DSS 4 / NIST 800-53 / ISO 27001 / SOC 2 control IDs."
            checked={draft.compliance_mapper_enabled}
            onChange={(v) => update('compliance_mapper_enabled', v)}
          />
        </div>
      </Card>

      <Card title="Reachability & VEX" subtitle="Snyk-style noise reduction for SCA findings">
        <div className="grid gap-4 sm:grid-cols-2">
          <ToggleRow
            label="Reachability analysis"
            description="Tag SCA findings as reachable/unreachable by walking the repo source tree."
            checked={draft.reachability_enabled}
            onChange={(v) => update('reachability_enabled', v)}
          />
          <ToggleRow
            label="Drop unreachable findings"
            description="Suppress unreachable findings up to a severity ceiling. KEV-listed CVEs always survive."
            checked={draft.reachability_drop_unreachable}
            onChange={(v) => update('reachability_drop_unreachable', v)}
          />
          <SelectInput
            label="Drop ceiling severity"
            value={draft.reachability_drop_max_severity}
            onChange={(v) => update('reachability_drop_max_severity', v)}
            options={[
              { value: 'info', label: 'Info' },
              { value: 'low', label: 'Low' },
              { value: 'medium', label: 'Medium' },
              { value: 'high', label: 'High' },
            ]}
          />
        </div>
        <div className="mt-5 grid gap-4 sm:grid-cols-2">
          <ToggleRow
            label="VEX attestations"
            description="Apply OpenVEX 0.2 / CycloneDX VEX 1.6 documents from the configured directory."
            checked={draft.vex_enabled}
            onChange={(v) => update('vex_enabled', v)}
          />
          <ToggleRow
            label="Suppress not_affected"
            description="Drop findings whose VEX status is not_affected / false_positive."
            checked={draft.vex_suppress_not_affected}
            onChange={(v) => update('vex_suppress_not_affected', v)}
          />
          <ToggleRow
            label="Suppress fixed"
            description="Drop findings whose VEX status is fixed / resolved."
            checked={draft.vex_suppress_fixed}
            onChange={(v) => update('vex_suppress_fixed', v)}
          />
        </div>
      </Card>

      <Card title="External enrichers" subtitle="OSV.dev (advisories) · GreyNoise (IP reputation)">
        <div className="grid gap-4 sm:grid-cols-2">
          <ToggleRow
            label="OSV.dev enricher"
            description="Cross-ecosystem fixed-in versions, GHSA IDs and advisory references for SCA findings. Free public API."
            checked={draft.osv_enricher_enabled}
            onChange={(v) => update('osv_enricher_enabled', v)}
          />
          <ToggleRow
            label="GreyNoise enricher"
            description="Annotate IP-target findings with GreyNoise reputation (noise / riot / classification)."
            checked={draft.greynoise_enricher_enabled}
            onChange={(v) => update('greynoise_enricher_enabled', v)}
          />
        </div>
      </Card>

      <Card
        title="Differential scanning"
        subtitle="Skip scanners whose input fingerprint matches a recent run"
      >
        <div className="grid gap-4 sm:grid-cols-2">
          <ToggleRow
            label="Differential cache"
            description="Reuse findings from a recent successful run when target fingerprint is unchanged."
            checked={draft.differential_enabled}
            onChange={(v) => update('differential_enabled', v)}
          />
          <NumberInput
            label="Cache TTL (seconds)"
            value={draft.differential_ttl_seconds}
            min={60}
            max={86400}
            onChange={(v) => update('differential_ttl_seconds', v)}
          />
        </div>
      </Card>

      <Card
        title="SOAR / ticketing webhooks"
        subtitle="Outbound notifications · inbound state-sync"
      >
        <div className="grid gap-4 sm:grid-cols-2">
          <ToggleRow
            label="Outbound notifier"
            description={
              draft.webhook_url_configured
                ? 'POST signed OCSF events to the configured webhook URL.'
                : 'Set RED_AGENT_WEBHOOK_URL + RED_AGENT_WEBHOOK_SECRET to enable.'
            }
            checked={draft.webhook_enabled}
            onChange={(v) => update('webhook_enabled', v)}
          />
          <SelectInput
            label="Min severity to forward"
            value={draft.webhook_min_severity}
            onChange={(v) => update('webhook_min_severity', v)}
            options={[
              { value: 'info', label: 'Info' },
              { value: 'low', label: 'Low' },
              { value: 'medium', label: 'Medium' },
              { value: 'high', label: 'High' },
              { value: 'critical', label: 'Critical' },
            ]}
          />
          <ToggleRow
            label="Inbound receiver"
            description="Mount POST /red-agent/webhooks/{provider} for SOAR state updates (Jira, ServiceNow, Linear, generic)."
            checked={draft.webhook_in_enabled}
            onChange={(v) => update('webhook_in_enabled', v)}
          />
          <ToggleRow
            label="Require inbound signature"
            description="Reject inbound webhooks without a valid HMAC signature."
            checked={draft.webhook_in_require_signature}
            onChange={(v) => update('webhook_in_require_signature', v)}
          />
          <ToggleRow
            label="Replay protection"
            description="Stripe-style timestamp-bound HMAC + nonce cache on both directions."
            checked={draft.webhook_replay_protection}
            onChange={(v) => update('webhook_replay_protection', v)}
          />
        </div>
      </Card>

      <Card
        title="Auto-remediation"
        subtitle="Open fix-PRs on upstream repos for SCA findings with osv_fixed_in"
      >
        <div className="grid gap-4 sm:grid-cols-2">
          <ToggleRow
            label="Auto-remediation endpoint"
            description="Mount POST /red-agent/findings/{id}/auto-remediate. Requires RED_AGENT_AUTO_REMEDIATION_GITHUB_TOKEN and per-finding repo metadata."
            checked={draft.auto_remediation_enabled}
            onChange={(v) => update('auto_remediation_enabled', v)}
          />
        </div>
      </Card>

      <Card title="Validated impact" subtitle="Noise reduction filters">
        <div className="grid gap-4 sm:grid-cols-2">
          <ToggleRow
            label="Validated impact only"
            description="Drop info/low findings without active confirmation."
            checked={draft.validated_impact_only}
            onChange={(v) => update('validated_impact_only', v)}
          />
          <NumberInput
            label="Min CVSS for validated"
            value={draft.validated_impact_min_cvss}
            min={0}
            max={10}
            step={0.1}
            onChange={(v) => update('validated_impact_min_cvss', v)}
          />
        </div>
      </Card>
    </div>
  );
}
