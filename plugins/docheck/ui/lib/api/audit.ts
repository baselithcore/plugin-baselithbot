import { authHeaders } from '../auth';

const BASE = process.env.NEXT_PUBLIC_API_BASE ?? 'http://127.0.0.1:8765/api/v1';

export interface AuditEntry {
  seq: number;
  ts: string;
  user_id: string | null;
  user_email?: string | null;
  action: string;
  resource: string | null;
  payload_hash: string;
  prev_hash: string;
  entry_hash: string;
  signature: string;
}

export interface AuditEntryDetail extends AuditEntry {
  valid: boolean;
  error: string | null;
}

export interface ChainStatus {
  ok: boolean;
  broken_seq: number | null;
  total_entries: number;
  pubkey: string;
  verified_at: string;
}

export interface AuditUserOption {
  user_id: string;
  email: string | null;
  display_name: string | null;
}

export interface AuditFilters {
  user_id?: string;
  action?: string;
  resource?: string;
  date_from?: string;
  date_to?: string;
}

export interface ListAuditParams extends AuditFilters {
  limit?: number;
  offset?: number;
}

export interface ListAuditResult {
  rows: AuditEntry[];
  total: number;
}

function buildQS(params: Record<string, string | number | undefined>): string {
  const qs = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v === undefined || v === null || v === '') continue;
    qs.set(k, String(v));
  }
  return qs.toString();
}

export async function listAuditPage(params: ListAuditParams = {}): Promise<ListAuditResult> {
  const qs = buildQS({
    limit: params.limit ?? 100,
    offset: params.offset ?? 0,
    user_id: params.user_id,
    action: params.action,
    resource: params.resource,
    date_from: params.date_from,
    date_to: params.date_to,
  });
  const res = await fetch(`${BASE}/audit/log?${qs}`, {
    headers: { ...authHeaders() },
  });
  if (!res.ok) throw new Error(`audit list failed: ${res.status}`);
  const total = Number(res.headers.get('X-Total-Count') ?? '0');
  const rows = (await res.json()) as AuditEntry[];
  return { rows, total };
}

export async function listAudit(limit = 100, offset = 0): Promise<AuditEntry[]> {
  const { rows } = await listAuditPage({ limit, offset });
  return rows;
}

export async function verifyAuditChain(): Promise<ChainStatus> {
  const res = await fetch(`${BASE}/audit/verify`, {
    headers: { ...authHeaders() },
  });
  if (!res.ok) throw new Error(`verify failed: ${res.status}`);
  return res.json();
}

export async function listAuditActions(): Promise<string[]> {
  const res = await fetch(`${BASE}/audit/actions`, {
    headers: { ...authHeaders() },
  });
  if (!res.ok) throw new Error(`actions failed: ${res.status}`);
  return res.json();
}

export async function listAuditUsers(): Promise<AuditUserOption[]> {
  const res = await fetch(`${BASE}/audit/users`, {
    headers: { ...authHeaders() },
  });
  if (!res.ok) throw new Error(`users failed: ${res.status}`);
  return res.json();
}

export async function getAuditEntry(seq: number): Promise<AuditEntryDetail> {
  const res = await fetch(`${BASE}/audit/${seq}`, {
    headers: { ...authHeaders() },
  });
  if (!res.ok) throw new Error(`detail failed: ${res.status}`);
  return res.json();
}

async function downloadBlob(url: string, filename: string): Promise<void> {
  const res = await fetch(url, { headers: { ...authHeaders() } });
  if (!res.ok) {
    const txt = await res.text().catch(() => '');
    throw new Error(`export failed: ${res.status} ${txt}`);
  }
  const blob = await res.blob();
  const objUrl = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = objUrl;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(objUrl);
}

export async function exportAuditCsv(filters: AuditFilters = {}): Promise<void> {
  const qs = buildQS({ ...filters });
  const ts = new Date().toISOString().replace(/[:.]/g, '-');
  await downloadBlob(`${BASE}/audit/export.csv?${qs}`, `audit-${ts}.csv`);
}

export async function exportAuditJson(filters: AuditFilters = {}): Promise<void> {
  const qs = buildQS({ ...filters });
  const ts = new Date().toISOString().replace(/[:.]/g, '-');
  await downloadBlob(`${BASE}/audit/export.json?${qs}`, `audit-${ts}.json`);
}
