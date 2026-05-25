import {
  AnalysisResponse,
  ChatResponsePayload,
  ChatStreamEvent,
  ConsoleConfig,
  KbListResponse,
  ProjectPlanPayload,
  JiraSyncResponse,
  ScenarioPayload,
  UserStoryPayload,
  JiraIssue,
  JiraProject,
  JiraProjectsResponse,
  JiraSettingsResponse,
  JiraSettingsPayload,
  JiraTestResult,
  AuthResponse,
  AuthUser,
} from '../types';

function resolveApiBase(): string {
  const configured = import.meta.env.VITE_API_BASE_URL?.trim();
  if (configured) {
    return configured.replace(/\/$/, '');
  }
  if (typeof window !== 'undefined') {
    return window.location.origin;
  }
  return '';
}

export const API_BASE = resolveApiBase();
const API_KEY = import.meta.env.VITE_API_KEY || '';
export const API_KEY_PRESENT = Boolean(API_KEY);

const TOKEN_STORAGE_KEY = 'agent-jira-token';

export function getStoredToken(): string | null {
  return localStorage.getItem(TOKEN_STORAGE_KEY);
}

export function setStoredToken(token: string): void {
  localStorage.setItem(TOKEN_STORAGE_KEY, token);
}

export function clearStoredToken(): void {
  localStorage.removeItem(TOKEN_STORAGE_KEY);
}

function buildAuthHeaders(): Record<string, string> {
  const headers: Record<string, string> = {};
  if (API_KEY) headers['X-API-Key'] = API_KEY;
  const token = getStoredToken();
  if (token) headers['Authorization'] = `Bearer ${token}`;
  return headers;
}

/** @deprecated Use buildAuthHeaders() — kept for backward compat */
export const AUTH_HEADERS: Record<string, string> = API_KEY ? { 'X-API-Key': API_KEY } : {};

type ChatResponseMetadata = Pick<
  ChatResponsePayload,
  | 'sources'
  | 'project_plan'
  | 'jira_issues'
  | 'created_jira_issues'
  | 'suggested_actions'
  | 'duration'
>;

function isChatResponseMetadata(value: unknown): value is Partial<ChatResponseMetadata> {
  if (!value || typeof value !== 'object') return false;
  const candidate = value as Record<string, unknown>;
  return (
    'jira_issues' in candidate ||
    'created_jira_issues' in candidate ||
    'project_plan' in candidate ||
    'sources' in candidate ||
    'suggested_actions' in candidate ||
    'duration' in candidate
  );
}

function extractTrailingPayload(rawText: string): {
  answer: string;
  payload: Partial<ChatResponseMetadata> | null;
} {
  const normalized = rawText.trimEnd();
  const lastNewline = normalized.lastIndexOf('\n');
  if (lastNewline === -1) {
    return { answer: rawText, payload: null };
  }

  const candidate = normalized.slice(lastNewline + 1).trim();
  if (!candidate.startsWith('{') || !candidate.endsWith('}')) {
    return { answer: rawText, payload: null };
  }

  try {
    const parsed = JSON.parse(candidate) as unknown;
    if (!isChatResponseMetadata(parsed)) {
      return { answer: rawText, payload: null };
    }
    return {
      answer: normalized.slice(0, lastNewline).trimEnd(),
      payload: parsed,
    };
  } catch {
    return { answer: rawText, payload: null };
  }
}

function buildChatResponse(
  answer: string,
  payload?: Partial<ChatResponseMetadata> | null
): ChatResponsePayload {
  return {
    answer,
    sources: payload?.sources || [],
    project_plan: payload?.project_plan || null,
    jira_issues: payload?.jira_issues || [],
    created_jira_issues: payload?.created_jira_issues || [],
    suggested_actions: payload?.suggested_actions || [],
    duration: payload?.duration,
  };
}

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...buildAuthHeaders(),
      ...(init?.headers || {}),
    },
    ...init,
  });

  if (!response.ok) {
    const detail = await response.text();
    // Se la risposta è HTML (inizia con <!doctype o <html), estraggo il titolo o uso un default
    if (
      detail.trim().toLowerCase().startsWith('<!doctype') ||
      detail.trim().toLowerCase().startsWith('<html')
    ) {
      throw new Error(
        `Errore Server (${response.status}): Il backend ha restituito una pagina HTML invece di JSON. Verifica la configurazione CORS o l'URL dell'API.`
      );
    }
    throw new Error(detail || `Richiesta al backend non riuscita (Stato ${response.status}).`);
  }

  const contentType = response.headers.get('content-type');
  if (contentType && contentType.includes('application/json')) {
    return (await response.json()) as T;
  }

  const text = await response.text();
  if (
    text.trim().toLowerCase().startsWith('<!doctype') ||
    text.trim().toLowerCase().startsWith('<html')
  ) {
    throw new Error(
      `Risposta Inattesa (${response.status}): Il backend ha restituito HTML invece del JSON atteso.`
    );
  }
  return text as unknown as T;
}

export async function sendChat(
  query: string,
  conversationId?: string,
  kbLabel?: string
): Promise<ChatResponsePayload> {
  return apiFetch<ChatResponsePayload>('/chat', {
    method: 'POST',
    body: JSON.stringify({
      query,
      conversation_id: conversationId,
      kb_label: kbLabel,
    }),
  });
}

export async function sendChatStream(
  query: string,
  conversationId?: string,
  kbLabel?: string,
  onChunk?: (chunk: string) => void,
  onEvent?: (event: ChatStreamEvent) => void
): Promise<ChatResponsePayload> {
  const response = await fetch(`${API_BASE}/chat/stream`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...buildAuthHeaders(),
    },
    body: JSON.stringify({
      query,
      conversation_id: conversationId,
      kb_label: kbLabel,
    }),
  });

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || 'Richiesta al backend non riuscita.');
  }

  const reader = response.body?.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  let finalPayload: ChatResponsePayload | null = null;
  let accumulatedText = '';

  if (!reader) {
    throw new Error('Stream non disponibile');
  }

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || ''; // Keep partial line in buffer

      for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed) continue;

        try {
          const event = JSON.parse(trimmed) as ChatStreamEvent & Record<string, any>;
          onEvent?.(event);
          const eventType = event.event_type ?? (event as any).type;
          if (eventType === 'token') {
            const chunk: string = event.text ?? event.content ?? '';
            if (chunk) {
              accumulatedText += chunk;
              if (onChunk) onChunk(chunk);
            }
          } else if (eventType === 'final_payload') {
            // Backend sends the payload fields at the top level
            const { event_type: _et, ...rest } = event;
            finalPayload = rest as ChatResponsePayload;
          } else if (eventType === 'error') {
            const msg: string = event.message ?? event.content ?? 'Errore durante lo streaming';
            console.error('Streaming error event:', msg);
            throw new Error(msg);
          }
          // Ignore status events (progress updates)
        } catch (e) {
          if (e instanceof Error && e.message !== trimmed) throw e;
          // Fallback: treat as raw text if not valid JSON
          console.warn('Failed to parse stream line as JSON:', trimmed, e);
          if (!trimmed.startsWith('{')) {
            accumulatedText += trimmed;
            if (onChunk) onChunk(trimmed);
          }
        }
      }
    }
  } finally {
    reader.releaseLock();
  }

  // Process any remaining content in buffer (e.g. last line without trailing newline)
  if (buffer.trim()) {
    try {
      const event = JSON.parse(buffer.trim()) as ChatStreamEvent & Record<string, any>;
      onEvent?.(event);
      const eventType = event.event_type ?? (event as any).type;
      if (eventType === 'token') {
        const chunk: string = event.text ?? event.content ?? '';
        if (chunk) {
          accumulatedText += chunk;
          if (onChunk) onChunk(chunk);
        }
      } else if (eventType === 'final_payload') {
        const { event_type: _et, ...rest } = event;
        finalPayload = rest as ChatResponsePayload;
      }
    } catch {
      // Not valid JSON, treat as raw text
      if (!buffer.trim().startsWith('{')) {
        accumulatedText += buffer.trim();
        if (onChunk) onChunk(buffer.trim());
      }
    }
  }

  if (finalPayload) {
    // Ensure we preserve the accumulated text if the final payload answer is missing
    return buildChatResponse(finalPayload.answer || accumulatedText, finalPayload);
  }

  return buildChatResponse(accumulatedText);
}

export async function fetchConfig(): Promise<ConsoleConfig> {
  return apiFetch<ConsoleConfig>('/console/config');
}

export async function fetchKbDocuments(): Promise<KbListResponse> {
  return apiFetch<KbListResponse>('/console/kb/documents');
}

export async function fetchKbCounts(
  label: string
): Promise<{ stories: number; test_cases: number }> {
  const params = new URLSearchParams({ label });
  return apiFetch<{ stories: number; test_cases: number }>(
    `/console/kb/counts?${params.toString()}`
  );
}

export async function analyzeDocument(formData: FormData): Promise<AnalysisResponse> {
  const response = await fetch(`${API_BASE}/console/analyze`, {
    method: 'POST',
    headers: {
      ...buildAuthHeaders(),
    },
    body: formData,
  });
  if (!response.ok) {
    const detail = await response.text();
    if (
      detail.trim().toLowerCase().startsWith('<!doctype') ||
      detail.trim().toLowerCase().startsWith('<html')
    ) {
      throw new Error(
        `Errore Analisi (${response.status}): Il backend ha restituito una pagina HTML invece di JSON. Questo accade spesso per errori di configurazione CORS o limiti di dimensione del file.`
      );
    }
    throw new Error(detail || `Analisi documento non riuscita (Stato ${response.status}).`);
  }

  const contentType = response.headers.get('content-type');
  if (contentType && contentType.includes('application/json')) {
    return (await response.json()) as AnalysisResponse;
  }

  const text = await response.text();
  if (
    text.trim().toLowerCase().startsWith('<!doctype') ||
    text.trim().toLowerCase().startsWith('<html')
  ) {
    throw new Error(
      `Risposta Analisi Inattesa (${response.status}): Il backend ha restituito HTML invece del JSON atteso.`
    );
  }
  throw new Error(
    `Risposta Analisi non valida: Atteso JSON, ricevuto ${contentType || 'formato sconosciuto'}.`
  );
}

type SyncJiraExtras = {
  kb?: AnalysisResponse['kb'];
  metadata?: Record<string, any>;
};

export async function syncJira(
  params: { plan: ProjectPlanPayload } & SyncJiraExtras
): Promise<JiraSyncResponse> {
  return apiFetch<JiraSyncResponse>('/console/jira/sync', {
    method: 'POST',
    body: JSON.stringify(params),
  });
}

export async function syncJiraStory(
  params: { story: UserStoryPayload } & SyncJiraExtras
): Promise<JiraSyncResponse> {
  return apiFetch<JiraSyncResponse>('/console/jira/sync', {
    method: 'POST',
    body: JSON.stringify(params),
  });
}

export async function syncJiraTestCases(params: {
  story_key: string;
  scenarios: ScenarioPayload[];
  issue_type?: string;
  project_key?: string | null;
  kb_label?: string;
  category?: string;
}): Promise<JiraSyncResponse> {
  return apiFetch<JiraSyncResponse>('/console/jira/testcases', {
    method: 'POST',
    body: JSON.stringify(params),
  });
}

export async function storeInKb(uploadPath: string, originalName?: string, analysisJson?: string) {
  const formData = new FormData();
  formData.append('file_path', uploadPath);
  if (originalName) {
    formData.append('original_name', originalName);
  }
  if (analysisJson) {
    formData.append('analysis_json', analysisJson);
  }
  const response = await fetch(`${API_BASE}/console/kb/store`, {
    method: 'POST',
    headers: {
      ...buildAuthHeaders(),
    },
    body: formData,
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || 'Salvataggio nella KB non riuscito.');
  }
  return response.json();
}

export async function deleteKbDocument(filePath: string) {
  const params = new URLSearchParams({ file_path: filePath });
  const response = await fetch(`${API_BASE}/console/kb/delete?${params.toString()}`, {
    method: 'DELETE',
    headers: {
      ...buildAuthHeaders(),
    },
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || 'Eliminazione documento non riuscita.');
  }
  return response.json();
}

export interface PlanReportResponse {
  html: string;
  filename: string;
}

export async function exportPlanReport(payload: {
  plan: ProjectPlanPayload;
  metadata?: Record<string, any>;
  summary?: string;
  jira_results?: JiraIssue[];
}): Promise<PlanReportResponse> {
  return apiFetch<PlanReportResponse>('/console/report', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function fetchJiraProjects(): Promise<JiraProjectsResponse> {
  return apiFetch<JiraProjectsResponse>('/console/jira/projects');
}

export async function previewJiraProjects(params: {
  base_url: string;
  email: string;
  api_token: string;
}): Promise<{ status: string; projects: JiraProject[]; message?: string }> {
  return apiFetch<{ status: string; projects: JiraProject[]; message?: string }>(
    '/console/jira/settings/projects',
    {
      method: 'POST',
      body: JSON.stringify(params),
    }
  );
}

export async function fetchJiraSearch(label: string | string[]): Promise<JiraSyncResponse> {
  const params = new URLSearchParams();
  const labels = Array.isArray(label) ? label : [label];
  labels.filter(Boolean).forEach((item) => params.append('label', item));
  return apiFetch<JiraSyncResponse>(`/console/jira/search?${params.toString()}`);
}

export async function fetchGraphData(path: string): Promise<any> {
  const params = new URLSearchParams({ path });
  return apiFetch<any>(`/console/kb/graph?${params.toString()}`);
}

export async function fetchJiraSettings(): Promise<JiraSettingsResponse> {
  return apiFetch<JiraSettingsResponse>('/console/jira/settings');
}

export interface SystemHealthResponse {
  status: string;
  ready: boolean;
  dependencies: Record<
    string,
    {
      name: string;
      enabled: boolean;
      required: boolean;
      ready: boolean;
      status: string;
      error?: string;
      [key: string]: any;
    }
  >;
}

export async function fetchSystemHealth(): Promise<SystemHealthResponse> {
  return apiFetch<SystemHealthResponse>('/health/ready');
}

export async function updateJiraSettings(
  payload: JiraSettingsPayload
): Promise<{ status: string; message: string }> {
  return apiFetch<{ status: string; message: string }>('/console/jira/settings', {
    method: 'PUT',
    body: JSON.stringify(payload),
  });
}

export async function testJiraConnection(params: {
  base_url: string;
  email: string;
  api_token: string;
}): Promise<JiraTestResult> {
  return apiFetch<JiraTestResult>('/console/jira/settings/test', {
    method: 'POST',
    body: JSON.stringify(params),
  });
}

// === Auth ===

export async function authRegister(params: {
  email: string;
  password: string;
  display_name?: string;
  organization?: string;
}): Promise<AuthResponse> {
  return apiFetch<AuthResponse>('/auth/register', {
    method: 'POST',
    body: JSON.stringify(params),
  });
}

export async function authLogin(params: {
  email: string;
  password: string;
}): Promise<AuthResponse> {
  return apiFetch<AuthResponse>('/auth/login', {
    method: 'POST',
    body: JSON.stringify(params),
  });
}

export async function authMe(): Promise<{ status: string; user: AuthUser; max_users?: number }> {
  return apiFetch<{ status: string; user: AuthUser; max_users?: number }>('/auth/me');
}

export async function listUsers(): Promise<{
  status: string;
  users: AuthUser[];
  max_users?: number;
}> {
  return apiFetch<{ status: string; users: AuthUser[]; max_users?: number }>('/auth/users');
}

export async function inviteUser(params: {
  email: string;
  password: string;
  display_name?: string;
  role?: string;
}): Promise<{ status: string; user: AuthUser }> {
  return apiFetch<{ status: string; user: AuthUser }>('/auth/users', {
    method: 'POST',
    body: JSON.stringify(params),
  });
}

export async function updateUserAdmin(
  userId: string,
  params: { display_name?: string; role?: string; is_active?: boolean }
): Promise<{ status: string; user: AuthUser }> {
  return apiFetch<{ status: string; user: AuthUser }>(`/auth/users/${userId}`, {
    method: 'PUT',
    body: JSON.stringify(params),
  });
}
