// Thin typed API client. The base path mirrors VITE_BASE_PATH so the SPA works
// both standalone (dev, '/') and mounted under '/baselithbrain' in production.
import type {
  BacklinkContext,
  GraphData,
  HistoryEntry,
  LinkSuggestion,
  MocCandidate,
  Note,
  NoteMeta,
  Revision,
  SearchHit,
  TagInfo,
  Template,
  TemplateMeta,
  TreeNode,
  Workspace,
  WorkspaceInfo,
} from './types';

/** ``?workspace=<id>`` suffix, or empty when unscoped (all notes). */
function wsParam(workspace?: string | null): string {
  return workspace ? `?workspace=${encodeURIComponent(workspace)}` : '';
}

const BASE = (import.meta.env.BASE_URL || '/').replace(/\/$/, '');

/**
 * Central-auth bearer header for every API call.
 *
 * baselithbrain is mounted same-origin under the host console, so it reads the
 * access token the auth login persists (localStorage ``auth_access_token`` — the
 * single key the `@auth` client uses). Without it the backend's context bridge
 * can't bind the user, so per-user (``personal``) vault scoping silently
 * collapses to the shared default vault. Empty object when logged out (anonymous
 * access still works exactly as before).
 */
function authHeaders(): Record<string, string> {
  const token = localStorage.getItem('auth_access_token');
  return token ? { Authorization: `Bearer ${token}` } : {};
}

/** Absolute URL for a vault asset path (``_assets/<name>`` or ``api/assets/…``). */
export function assetUrl(pathOrUrl: string): string {
  const clean = pathOrUrl.replace(/^_assets\//, 'api/assets/').replace(/^\//, '');
  return `${BASE}/${clean}`;
}

/**
 * Fetch a file with the bearer header and trigger a browser download. Used for
 * exports: a plain ``<a download>`` cannot send the Authorization header, so the
 * backend context bridge would bind no user and scope to the wrong vault.
 */
async function downloadFile(path: string, fallbackName: string): Promise<void> {
  const res = await fetch(`${BASE}${path}`, { headers: authHeaders() });
  if (!res.ok) throw new Error(`${res.status}: ${await res.text().catch(() => res.statusText)}`);
  const disposition = res.headers.get('content-disposition') || '';
  const match = /filename="?([^"]+)"?/.exec(disposition);
  const name = match?.[1] || fallbackName;
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = name;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...authHeaders(),
      ...((init?.headers as Record<string, string> | undefined) ?? {}),
    },
  });
  if (!res.ok) {
    const detail = await res.text().catch(() => res.statusText);
    throw new Error(`${res.status}: ${detail}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export const api = {
  listNotes: (workspace?: string | null) => req<NoteMeta[]>(`/api/notes${wsParam(workspace)}`),
  tree: (workspace?: string | null) => req<TreeNode[]>(`/api/notes/tree${wsParam(workspace)}`),
  getNote: (id: string) => req<Note>(`/api/notes/${id}`),
  createNote: (data: {
    title: string;
    body?: string;
    tags?: string[];
    parent?: string | null;
    workspace?: string | null;
  }) => req<Note>('/api/notes', { method: 'POST', body: JSON.stringify(data) }),
  updateNote: (id: string, patch: { title?: string; body?: string; tags?: string[] }) =>
    req<Note>(`/api/notes/${id}`, { method: 'PUT', body: JSON.stringify(patch) }),
  moveNote: (id: string, payload: { parent: string | null; order?: number }) =>
    req<Note>(`/api/notes/${id}/move`, { method: 'POST', body: JSON.stringify(payload) }),
  assignNoteWorkspace: (id: string, workspace: string) =>
    req<Note>(`/api/notes/${id}/workspace`, {
      method: 'POST',
      body: JSON.stringify({ workspace }),
    }),
  deleteNote: (id: string) => req<{ deleted: boolean }>(`/api/notes/${id}`, { method: 'DELETE' }),

  // ---- workspaces (logical note groupings) ----
  listWorkspaces: () => req<WorkspaceInfo[]>('/api/workspaces'),
  createWorkspace: (data: { name: string; color?: string | null; description?: string }) =>
    req<Workspace>('/api/workspaces', { method: 'POST', body: JSON.stringify(data) }),
  updateWorkspace: (
    id: string,
    patch: { name?: string; color?: string | null; description?: string; order?: number }
  ) => req<Workspace>(`/api/workspaces/${id}`, { method: 'PUT', body: JSON.stringify(patch) }),
  deleteWorkspace: (id: string) =>
    req<{ deleted: boolean; reassigned: number }>(`/api/workspaces/${id}`, { method: 'DELETE' }),

  uploadAsset: async (file: File): Promise<{ name: string; path: string; url: string }> => {
    const form = new FormData();
    form.append('file', file);
    // No Content-Type — the browser sets the multipart boundary; auth only.
    const res = await fetch(`${BASE}/api/assets`, {
      method: 'POST',
      body: form,
      headers: authHeaders(),
    });
    if (!res.ok) throw new Error(`${res.status}: ${await res.text().catch(() => res.statusText)}`);
    return res.json();
  },

  search: (q: string, topK = 20, workspace?: string | null) =>
    req<SearchHit[]>(
      `/api/search?q=${encodeURIComponent(q)}&top_k=${topK}` +
        (workspace ? `&workspace=${encodeURIComponent(workspace)}` : '')
    ),

  graph: (opts?: { tags?: boolean; derived?: boolean; workspace?: string | null }) =>
    req<GraphData>(
      `/api/graph?tags=${opts?.tags ?? true}&derived=${opts?.derived ?? false}` +
        (opts?.workspace ? `&workspace=${encodeURIComponent(opts.workspace)}` : '')
    ),
  neighborhood: (id: string, hops = 1) =>
    req<GraphData>(`/api/graph/neighborhood/${id}?hops=${hops}`),
  mocs: (minSize = 4) => req<MocCandidate[]>(`/api/graph/mocs?min_size=${minSize}`),
  suggestions: (id: string, topK = 6) =>
    req<LinkSuggestion[]>(`/api/graph/suggestions/${id}?top_k=${topK}`),

  backlinks: (id: string) => req<BacklinkContext[]>(`/api/notes/${id}/backlinks`),

  reindex: () => req<{ ready: boolean; notes: number }>('/api/reindex', { method: 'POST' }),

  // ---- tags ----
  tags: (workspace?: string | null) => req<TagInfo[]>(`/api/tags${wsParam(workspace)}`),

  // ---- daily note (idempotent get-or-create) ----
  openDaily: (opts?: { date?: string | null; template?: string | null }) =>
    req<Note>('/api/daily', {
      method: 'POST',
      body: JSON.stringify({ date: opts?.date ?? null, template: opts?.template ?? null }),
    }),

  // ---- templates ----
  listTemplates: () => req<TemplateMeta[]>('/api/templates'),
  getTemplate: (id: string) => req<Template>(`/api/templates/${id}`),
  createTemplate: (data: { name: string; body: string }) =>
    req<Template>('/api/templates', { method: 'POST', body: JSON.stringify(data) }),
  deleteTemplate: (id: string) =>
    req<{ deleted: boolean }>(`/api/templates/${id}`, { method: 'DELETE' }),

  // ---- version history ----
  history: (id: string) => req<HistoryEntry[]>(`/api/notes/${id}/history`),
  revision: (id: string, version: string) => req<Revision>(`/api/notes/${id}/history/${version}`),
  restoreRevision: (id: string, version: string) =>
    req<Note>(`/api/notes/${id}/history/${version}/restore`, { method: 'POST' }),

  // ---- trash (soft delete) ----
  trash: () => req<NoteMeta[]>('/api/trash'),
  restoreTrash: (id: string) => req<Note>(`/api/trash/${id}/restore`, { method: 'POST' }),
  purgeTrash: (id: string) => req<{ purged: boolean }>(`/api/trash/${id}`, { method: 'DELETE' }),
  emptyTrash: () => req<{ purged: number }>('/api/trash', { method: 'DELETE' }),

  // ---- export (auth-aware blob download; an <a href> would omit the bearer
  // token and the backend would scope to the wrong/anonymous vault) ----
  downloadNote: (id: string) => downloadFile(`/api/notes/${id}/export`, `${id}.md`),
  downloadVault: (workspace?: string | null) =>
    downloadFile(`/api/export${wsParam(workspace)}`, `${workspace || 'vault'}.zip`),

  aiStatus: () => req<import('./types').AiStatus>('/api/ai/status'),

  aiTransform: (action: string, text: string, title = '') =>
    req<import('./types').TransformResult>('/api/ai/transform', {
      method: 'POST',
      body: JSON.stringify({ action, text, title }),
    }),

  // Deep research: a bounded multi-hop ReAct run over the vault. One long
  // request (no streaming) returning a cited report + the reasoning trace.
  aiResearch: (question: string, signal?: AbortSignal) =>
    req<import('./types').ResearchResult>('/api/ai/research', {
      method: 'POST',
      body: JSON.stringify({ question }),
      signal,
    }),

  // ---- conversations (persisted chat threads) ----
  listConversations: (workspace?: string | null) =>
    req<import('./types').ConversationMeta[]>(`/api/ai/conversations${wsParam(workspace)}`),
  getConversation: (id: string) =>
    req<import('./types').Conversation>(`/api/ai/conversations/${id}`),
  renameConversation: (id: string, title: string) =>
    req<import('./types').Conversation>(`/api/ai/conversations/${id}`, {
      method: 'PATCH',
      body: JSON.stringify({ title }),
    }),
  clearConversation: (id: string) =>
    req<import('./types').Conversation>(`/api/ai/conversations/${id}/clear`, {
      method: 'POST',
    }),
  deleteConversation: (id: string) =>
    req<{ deleted: boolean }>(`/api/ai/conversations/${id}`, { method: 'DELETE' }),

  // Stream a RAG answer for a thread. The server owns conversational memory, so
  // we send only the question + thread id (+ workspace when opening a thread).
  // Parses NDJSON line-by-line, invoking the handler per event
  // (meta / token / sources / error). Resolves when the stream closes.
  aiChat: async (
    question: string,
    opts: { conversationId?: string | null; workspace?: string | null },
    onEvent: (e: import('./types').ChatEvent) => void,
    signal?: AbortSignal
  ): Promise<void> => {
    const res = await fetch(`${BASE}/api/ai/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...authHeaders() },
      body: JSON.stringify({
        question,
        conversation_id: opts.conversationId ?? null,
        workspace: opts.workspace ?? null,
      }),
      signal,
    });
    if (!res.ok || !res.body) {
      onEvent({ type: 'error', message: `${res.status}` });
      return;
    }
    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buf = '';
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      buf += decoder.decode(value, { stream: true });
      const lines = buf.split('\n');
      buf = lines.pop() ?? '';
      for (const line of lines) {
        if (!line.trim()) continue;
        try {
          onEvent(JSON.parse(line));
        } catch {
          /* ignore partial/garbled line */
        }
      }
    }
  },
};
