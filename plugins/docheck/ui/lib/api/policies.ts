import { authHeaders } from '../auth';
import { BASE, jsonOrThrow, postFormWithProgress, type UploadProgress } from './_base';
import type {
  IngestPolicyRow,
  PolicyCreatePayload,
  PolicyPatchPayload,
  PolicyRow,
  RulePayload,
  RuleRow,
} from './types';

export async function listPolicies(): Promise<PolicyRow[]> {
  const res = await fetch(`${BASE}/policies`, {
    headers: { ...authHeaders() },
  });
  if (!res.ok) throw new Error(`policies failed: ${res.status}`);
  return res.json();
}

export async function listRules(policyId: string, version?: string): Promise<RuleRow[]> {
  const qs = version ? `?version=${encodeURIComponent(version)}` : '';
  const res = await fetch(`${BASE}/policies/${policyId}/rules${qs}`, {
    headers: { ...authHeaders() },
  });
  if (!res.ok) throw new Error(`rules failed: ${res.status}`);
  return res.json();
}

export async function createPolicy(body: PolicyCreatePayload): Promise<PolicyRow> {
  const res = await fetch(`${BASE}/policies`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeaders() },
    body: JSON.stringify(body),
  });
  return jsonOrThrow(res, 'create policy');
}

export async function updatePolicy(
  id: string,
  version: string,
  patch: PolicyPatchPayload
): Promise<PolicyRow> {
  const res = await fetch(
    `${BASE}/policies/${encodeURIComponent(id)}/${encodeURIComponent(version)}`,
    {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json', ...authHeaders() },
      body: JSON.stringify(patch),
    }
  );
  return jsonOrThrow(res, 'update policy');
}

export async function setPolicyActive(
  id: string,
  version: string,
  active: boolean
): Promise<{ id: string; version: string; active: boolean }> {
  const res = await fetch(
    `${BASE}/policies/${encodeURIComponent(id)}/${encodeURIComponent(version)}/active`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...authHeaders() },
      body: JSON.stringify({ active }),
    }
  );
  return jsonOrThrow(res, 'activate');
}

export async function clonePolicy(
  id: string,
  version: string,
  newVersion: string
): Promise<PolicyRow> {
  const res = await fetch(
    `${BASE}/policies/${encodeURIComponent(id)}/${encodeURIComponent(version)}/clone`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...authHeaders() },
      body: JSON.stringify({ new_version: newVersion }),
    }
  );
  return jsonOrThrow(res, 'clone');
}

export async function deletePolicy(id: string, version: string, force = false): Promise<void> {
  const qs = force ? '?force=true' : '';
  const res = await fetch(
    `${BASE}/policies/${encodeURIComponent(id)}/${encodeURIComponent(version)}${qs}`,
    { method: 'DELETE', headers: { ...authHeaders() } }
  );
  if (!res.ok) {
    const txt = await res.text().catch(() => '');
    const err = new Error(`delete policy: ${res.status} ${txt}`) as Error & {
      status?: number;
      detail?: string;
    };
    err.status = res.status;
    try {
      err.detail = JSON.parse(txt)?.detail ?? txt;
    } catch {
      err.detail = txt;
    }
    throw err;
  }
}

export async function addRule(id: string, version: string, payload: RulePayload): Promise<RuleRow> {
  const res = await fetch(
    `${BASE}/policies/${encodeURIComponent(id)}/${encodeURIComponent(version)}/rules`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...authHeaders() },
      body: JSON.stringify(payload),
    }
  );
  return jsonOrThrow(res, 'add rule');
}

export async function updateRule(
  id: string,
  version: string,
  ruleId: string,
  patch: Partial<RulePayload>
): Promise<RuleRow> {
  const res = await fetch(
    `${BASE}/policies/${encodeURIComponent(id)}/${encodeURIComponent(version)}/rules/${encodeURIComponent(ruleId)}`,
    {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json', ...authHeaders() },
      body: JSON.stringify(patch),
    }
  );
  return jsonOrThrow(res, 'update rule');
}

export async function deleteRule(id: string, version: string, ruleId: string): Promise<void> {
  const res = await fetch(
    `${BASE}/policies/${encodeURIComponent(id)}/${encodeURIComponent(version)}/rules/${encodeURIComponent(ruleId)}`,
    { method: 'DELETE', headers: { ...authHeaders() } }
  );
  if (!res.ok) {
    const txt = await res.text().catch(() => '');
    throw new Error(`delete rule: ${res.status} ${txt}`);
  }
}

export async function ingestPolicyFromUrl(url: string): Promise<IngestPolicyRow> {
  const res = await fetch(`${BASE}/policies/ingest/url`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeaders() },
    body: JSON.stringify({ url }),
  });
  return jsonOrThrow(res, 'ingest url');
}

export async function ingestPolicyFromDocument(
  file: File,
  onProgress?: UploadProgress
): Promise<IngestPolicyRow> {
  const fd = new FormData();
  fd.append('file', file);
  return postFormWithProgress<IngestPolicyRow>(
    `${BASE}/policies/ingest/document`,
    fd,
    authHeaders(),
    onProgress,
    'ingest document'
  );
}

export interface SuggestedRule {
  rule_type: string;
  severity: string;
  excerpt: string;
  matcher?: string | null;
  rationale?: string | null;
}

export async function suggestRulesFromUrl(
  policyId: string,
  version: string,
  url: string
): Promise<SuggestedRule[]> {
  const res = await fetch(
    `${BASE}/policies/${encodeURIComponent(policyId)}/${encodeURIComponent(version)}/suggest-rules`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...authHeaders() },
      body: JSON.stringify({ source_url: url }),
    }
  );
  const j = await jsonOrThrow<{ suggestions: SuggestedRule[] }>(res, 'suggest rules');
  return j.suggestions;
}

export async function suggestRulesFromDocument(
  policyId: string,
  version: string,
  file: File,
  onProgress?: UploadProgress
): Promise<SuggestedRule[]> {
  const fd = new FormData();
  fd.append('file', file);
  const j = await postFormWithProgress<{ suggestions: SuggestedRule[] }>(
    `${BASE}/policies/${encodeURIComponent(policyId)}/${encodeURIComponent(version)}/suggest-rules/document`,
    fd,
    authHeaders(),
    onProgress,
    'suggest rules document'
  );
  return j.suggestions;
}

export async function suggestRulesFromText(
  policyId: string,
  version: string,
  text: string
): Promise<SuggestedRule[]> {
  const res = await fetch(
    `${BASE}/policies/${encodeURIComponent(policyId)}/${encodeURIComponent(version)}/suggest-rules`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...authHeaders() },
      body: JSON.stringify({ source_text: text }),
    }
  );
  const j = await jsonOrThrow<{ suggestions: SuggestedRule[] }>(res, 'suggest rules');
  return j.suggestions;
}

export async function importPolicyYaml(
  file: File,
  onProgress?: UploadProgress
): Promise<PolicyRow> {
  const fd = new FormData();
  fd.append('file', file);
  return postFormWithProgress<PolicyRow>(
    `${BASE}/policies/import`,
    fd,
    authHeaders(),
    onProgress,
    'import yaml'
  );
}

export async function exportPolicyYaml(id: string, version: string): Promise<void> {
  const res = await fetch(
    `${BASE}/policies/${encodeURIComponent(id)}/${encodeURIComponent(version)}/export.yaml`,
    { headers: { ...authHeaders() } }
  );
  if (!res.ok) throw new Error(`export yaml: ${res.status}`);
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `${id}-${version}.yaml`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}
