import { authHeaders } from "../auth";

const BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://127.0.0.1:8765/api/v1";

export interface RuntimeInfo {
  app_name: string;
  version: string;
  debug: boolean;
  llm_base_url: string;
  llm_primary_model: string;
  llm_fallback_model: string;
  llm_temperature: number;
  llm_top_p: number;
  embedding_model: string;
  ocr_engine: string;
  vector_backend: string;
  db_backend: string;
  multitenant_enabled: boolean;
  db_encryption_enabled: boolean;
  oidc_enabled: boolean;
  retention_default_days: number;
}

export interface StorageStats {
  db_path: string;
  db_size_bytes: number;
  chroma_path: string;
  chroma_size_bytes: number;
  storage_root: string;
  storage_size_bytes: number;
  documents: number;
  chunks: number;
  reports: number;
  policies: number;
  audit_entries: number;
  users: number;
  verdict_cache: number;
  embedding_cache: number;
}

export interface LLMProbeResult {
  ok: boolean;
  base_url: string;
  latency_ms: number;
  models: string[];
  error: string | null;
}

export interface CacheState {
  metrics: { hits: number; misses: number; total: number; hit_ratio: number };
  verdict_rows: number;
  embedding_rows: number;
}

export interface RetentionInfo {
  days: number;
  source: "config" | "override";
}

async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    headers: { ...(init?.headers || {}), ...authHeaders() },
  });
  if (!res.ok) {
    const txt = await res.text().catch(() => "");
    throw new Error(`${path} ${res.status}: ${txt || res.statusText}`);
  }
  return res.status === 204 ? (undefined as T) : ((await res.json()) as T);
}

export const getRuntimeInfo = () => api<RuntimeInfo>("/system/runtime");
export const getStorageStats = () => api<StorageStats>("/system/storage");
export const getCacheState = () => api<CacheState>("/system/cache");
export const getRetention = () => api<RetentionInfo>("/system/retention");

export const probeLLM = () =>
  api<LLMProbeResult>("/system/llm/probe", { method: "POST" });

export const resetCacheMetrics = () =>
  api<{ ok: boolean }>("/system/cache/reset", { method: "POST" });

export const setRetentionDays = (days: number) =>
  api<RetentionInfo>("/system/retention", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ days }),
  });

export const changePassword = (
  current_password: string,
  new_password: string,
) =>
  api<{ ok: boolean }>("/auth/change-password", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ current_password, new_password }),
  });
