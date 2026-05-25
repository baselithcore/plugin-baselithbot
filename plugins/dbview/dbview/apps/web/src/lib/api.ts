import axios, { type AxiosRequestConfig } from 'axios';
import { getAccessToken, refreshSession, setSession } from './auth.js';
import type {
  AuthConfig,
  BootstrapRequest,
  BootstrapStatusResponse,
  ChangePasswordRequest,
  ConnectionSharing,
  ConnectionSummary,
  CreateConnectionDto,
  DumpFormat,
  ExecuteQueryRequest,
  ExecuteQueryResponse,
  HistoryEntry,
  InviteRequest,
  ListHistoryQuery,
  ListHistoryResponse,
  LoginRequest,
  LoginResponse,
  LlmCredentialStatus,
  Nl2QueryAskRequest,
  Nl2QueryAskResponse,
  Nl2SqlRequest,
  Nl2SqlResponse,
  OllamaModelsResponse,
  RegisterRequest,
  RemoteLlmProvider,
  RemoteModelsResponse,
  SetLlmCredentialRequest,
  TestLlmCredentialRequest,
  TestLlmCredentialResponse,
  UnifiedSchema,
  UpdateUserRequest,
  UploadDumpResponse,
  UserPublic,
} from '@dbview/shared';

// Plugin-mode override. When dbview is embedded inside another host
// (e.g. baselithcore-enterprise) the reverse proxy may mount the API
// under a non-root prefix such as ``/api/dbview``. ``VITE_API_BASE_URL``
// — read at build time — replaces the default ``/api`` while preserving
// every downstream relative path. Unset = upstream standalone behaviour.
export const API_BASE_URL = (
  (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? '/api'
).replace(/\/+$/, '');

export const http = axios.create({
  baseURL: API_BASE_URL,
  // 300s aligns with nginx proxy_read_timeout. Salesforce Data Cloud queries
  // and large NL2SQL turns can exceed 2 minutes on cold paths.
  timeout: 300_000,
  withCredentials: true,
});

http.interceptors.request.use((config) => {
  if (typeof window !== 'undefined') {
    const key = localStorage.getItem('dbview_api_key');
    if (key) {
      config.headers.set('X-API-Key', key);
    }
  }
  const token = getAccessToken();
  if (token) {
    config.headers.set('Authorization', `Bearer ${token}`);
  }
  return config;
});

http.interceptors.response.use(undefined, async (err) => {
  if (axios.isAxiosError(err)) {
    const status = err.response?.status;
    const data = err.response?.data as
      | { code?: string; message?: string; error?: string; issues?: unknown }
      | undefined;
    const original = err.config as (AxiosRequestConfig & { _retried?: boolean }) | undefined;
    const isAuthEndpoint = typeof original?.url === 'string' && original.url.includes('/auth/');

    if (status === 401 && original && !original._retried && !isAuthEndpoint) {
      original._retried = true;
      const refreshed = await refreshSession();
      if (refreshed) {
        original.headers = original.headers ?? {};
        (original.headers as Record<string, string>)['Authorization'] =
          `Bearer ${refreshed.accessToken}`;
        return http.request(original);
      }
      setSession(null, null);
    }

    const msg =
      data?.message ??
      (typeof data?.error === 'string' ? data.error : undefined) ??
      (status ? `Request failed (${status})` : err.message);
    const e = new Error(msg) as Error & {
      code?: string;
      status?: number;
      issues?: unknown;
    };
    e.code = data?.code;
    e.status = status;
    e.issues = data?.issues;
    return Promise.reject(e);
  }
  return Promise.reject(err);
});

export const api = {
  listConnections: () => http.get<ConnectionSummary[]>('/connections').then((r) => r.data),
  createConnection: (dto: CreateConnectionDto) =>
    http.post<ConnectionSummary>('/connections', dto).then((r) => r.data),
  testConnection: (dto: CreateConnectionDto) =>
    http.post<{ ok: true }>('/connections/test', dto).then((r) => r.data),
  deleteConnection: (id: string) => http.delete(`/connections/${id}`).then(() => undefined),
  updateConnectionSharing: (id: string, sharing: ConnectionSharing) =>
    http.patch<ConnectionSummary>(`/connections/${id}/sharing`, { sharing }).then((r) => r.data),
  uploadDump: async (file: File, format: DumpFormat): Promise<UploadDumpResponse> => {
    const buf = await file.arrayBuffer();
    const contentBase64 = bufferToBase64(buf);
    const safeName = file.name.replace(/[^A-Za-z0-9._-]/g, '_').slice(0, 100) || 'dump.bin';
    return http
      .post<UploadDumpResponse>('/connections/upload-dump', {
        filename: safeName,
        format,
        contentBase64,
      })
      .then((r) => r.data);
  },
  getSchema: (id: string, refresh = false) =>
    http
      .get<UnifiedSchema>(`/schema/${id}`, { params: refresh ? { refresh: 1 } : {} })
      .then((r) => r.data),
  translate: (req: Nl2SqlRequest) => http.post<Nl2SqlResponse>('/nl2sql', req).then((r) => r.data),
  ask: (req: Nl2QueryAskRequest) =>
    http.post<Nl2QueryAskResponse>('/nl2sql/ask', req).then((r) => r.data),
  execute: (req: ExecuteQueryRequest) =>
    http.post<ExecuteQueryResponse>('/query/execute', req).then((r) => r.data),
  sample: (req: { connectionId: string; tableId: string; rowLimit?: number }) =>
    http.post<ExecuteQueryResponse>('/query/sample', req).then((r) => r.data),
  listOllamaModels: () => http.get<OllamaModelsResponse>('/llm/ollama/models').then((r) => r.data),
  getLlmCredential: (provider: RemoteLlmProvider) =>
    http.get<LlmCredentialStatus>(`/llm/providers/${provider}/credential`).then((r) => r.data),
  setLlmCredential: (provider: RemoteLlmProvider, body: SetLlmCredentialRequest) =>
    http
      .put<LlmCredentialStatus>(`/llm/providers/${provider}/credential`, body)
      .then((r) => r.data),
  deleteLlmCredential: (provider: RemoteLlmProvider) =>
    http.delete<LlmCredentialStatus>(`/llm/providers/${provider}/credential`).then((r) => r.data),
  testLlmCredential: (provider: RemoteLlmProvider, body: TestLlmCredentialRequest = {}) =>
    http
      .post<TestLlmCredentialResponse>(`/llm/providers/${provider}/test`, body)
      .then((r) => r.data),
  listRemoteModels: (provider: RemoteLlmProvider) =>
    http.get<RemoteModelsResponse>(`/llm/providers/${provider}/models`).then((r) => r.data),
  listHistory: (query: Partial<ListHistoryQuery> = {}) =>
    http.get<ListHistoryResponse>('/history', { params: query }).then((r) => r.data),
  toggleFavorite: (id: string, favorite: boolean) =>
    http.patch<HistoryEntry>(`/history/${id}/favorite`, { favorite }).then((r) => r.data),
  deleteHistory: (id: string) => http.delete(`/history/${id}`).then(() => undefined),
  clearHistory: (connectionId?: string) =>
    http
      .delete<{ removed: number }>('/history', { params: connectionId ? { connectionId } : {} })
      .then((r) => r.data),
  authConfig: () => http.get<AuthConfig>('/auth/config').then((r) => r.data),
  bootstrapStatus: () =>
    http.get<BootstrapStatusResponse>('/auth/bootstrap/status').then((r) => r.data),
  bootstrap: (body: BootstrapRequest) =>
    http.post<LoginResponse>('/auth/bootstrap', body).then((r) => r.data),
  login: (body: LoginRequest) => http.post<LoginResponse>('/auth/login', body).then((r) => r.data),
  register: (body: RegisterRequest) =>
    http.post<LoginResponse>('/auth/register', body).then((r) => r.data),
  logout: () => http.post('/auth/logout').then(() => undefined),
  changePassword: (body: ChangePasswordRequest) =>
    http.post<LoginResponse>('/auth/change-password', body).then((r) => r.data),
  listUsers: () => http.get<UserPublic[]>('/auth/users').then((r) => r.data),
  inviteUser: (body: InviteRequest) =>
    http.post<UserPublic>('/auth/users', body).then((r) => r.data),
  updateUser: (id: string, body: UpdateUserRequest) =>
    http.patch<UserPublic>(`/auth/users/${id}`, body).then((r) => r.data),
  deleteUser: (id: string) => http.delete(`/auth/users/${id}`).then(() => undefined),
};

function bufferToBase64(buf: ArrayBuffer): string {
  const bytes = new Uint8Array(buf);
  const chunk = 0x8000;
  let bin = '';
  for (let i = 0; i < bytes.length; i += chunk) {
    bin += String.fromCharCode(...bytes.subarray(i, i + chunk));
  }
  return btoa(bin);
}
