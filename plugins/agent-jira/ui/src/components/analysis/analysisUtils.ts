import { AnalysisResponse, JiraIssue } from '../../types';

export const mergeJiraResults = (existing: JiraIssue[], incoming: JiraIssue[]) => {
  const merged = [...existing];
  incoming.forEach((issue) => {
    const key = issue.key || issue.summary;
    if (!key) {
      merged.push(issue);
      return;
    }
    const idx = merged.findIndex((entry) => entry.key === key || entry.summary === key);
    if (idx >= 0) {
      merged[idx] = issue;
    } else {
      merged.push(issue);
    }
  });
  return merged;
};

export const inferDocId = (
  payload: AnalysisResponse | null,
  fallbackKb?: string,
  fallbackFile?: File | null
) => {
  const meta = payload?.metadata || {};
  return (
    meta.kb_label ||
    payload?.kb?.label ||
    meta.doc_label ||
    meta.kb_path ||
    meta.path ||
    meta.file_name ||
    meta.filename ||
    meta.name ||
    meta.original_name ||
    payload?.kb?.label ||
    fallbackKb ||
    fallbackFile?.name ||
    null
  );
};

export const preserveExistingJiraResults = (
  next: AnalysisResponse,
  prev: AnalysisResponse | null,
  fallbackKb?: string,
  fallbackFile?: File | null
): AnalysisResponse => {
  if (!prev) return next;
  const prevDocId = inferDocId(prev, fallbackKb, fallbackFile);
  const nextDocId = inferDocId(next, fallbackKb, fallbackFile);
  const hasNextResults = Array.isArray(next.jira?.results) && next.jira.results.length > 0;
  if (prevDocId && nextDocId && prevDocId === nextDocId && !hasNextResults) {
    return {
      ...next,
      jira: {
        ...next.jira,
        results: prev.jira?.results || [],
      },
    };
  }
  return next;
};

export const historicalIssuesForDoc = (
  docId: string | null,
  current: JiraIssue[],
  persistedJiraByDoc: Record<string, JiraIssue[]>
) => {
  if (!docId) return [];
  const previous = persistedJiraByDoc[docId] || [];
  const seen = new Set<string>(
    current.map((issue) => (issue.key || issue.summary || '').toString())
  );
  return previous.filter((issue) => {
    const key = (issue.key || issue.summary || '').toString();
    if (!key) return false;
    return !seen.has(key);
  });
};

export const slugifyFilename = (name: string, fallback: string): string => {
  const stem = name.replace(/\.[^/.]+$/, '');
  const slug = stem
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '');
  return slug || fallback;
};

const fnv1aHex = (input: string): string => {
  let h = 0x811c9dc5;
  for (let i = 0; i < input.length; i++) {
    h ^= input.charCodeAt(i);
    h = (h + ((h << 1) + (h << 4) + (h << 7) + (h << 8) + (h << 24))) >>> 0;
  }
  return h.toString(16).padStart(8, '0').slice(0, 6);
};

export const sha1Hex = async (input: string): Promise<string> => {
  if (typeof crypto !== 'undefined' && crypto.subtle?.digest) {
    try {
      const data = new TextEncoder().encode(input);
      const digest = await crypto.subtle.digest('SHA-1', data);
      return Array.from(new Uint8Array(digest))
        .map((b) => b.toString(16).padStart(2, '0'))
        .join('')
        .slice(0, 6);
    } catch {
      // fall through to fnv1a fallback (non-secure context)
    }
  }
  return fnv1aHex(input);
};

export const buildDeterministicLabel = async (
  filename: string,
  namespace: 'kb' | 'analysis'
): Promise<string> => {
  const fallback = namespace === 'kb' ? 'documento' : 'document';
  // Rimuovi estensione dal filename per slug E digest
  const stem = filename.replace(/\.[^/.]+$/, '');
  const slug = slugifyFilename(stem, fallback);
  const digest = await sha1Hex(`${namespace}::${stem}`); // Usa stem senza estensione
  return `${slug}-${digest}`.slice(0, 50);
};
