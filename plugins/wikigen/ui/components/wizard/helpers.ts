import { ApiError } from '../../lib/api';

export function humanise(name: string): string {
  return name
    .replace(/[_-]/g, ' ')
    .split(' ')
    .filter(Boolean)
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(' ');
}

export function humanError(err: unknown): string {
  if (err instanceof ApiError) {
    try {
      const parsed = JSON.parse(err.message) as { detail?: unknown };
      if (typeof parsed.detail === 'string') return parsed.detail;
      if (Array.isArray(parsed.detail)) {
        return parsed.detail
          .map((d: { msg?: string; loc?: unknown[] }) => d.msg ?? '')
          .filter(Boolean)
          .join('; ');
      }
    } catch {
      /* not JSON */
    }
    return `${err.status}: ${err.message.slice(0, 200)}`;
  }
  return err instanceof Error ? err.message : 'errore sconosciuto';
}

export function shorten(p: string, max = 60): string {
  if (p.length <= max) return p;
  return '…' + p.slice(p.length - max + 1);
}

export type UploadProgress = {
  phase: 'idle' | 'theme' | 'logo' | 'docs' | 'done';
  current: number;
  total: number;
};

export function renderProgressLabel(p: UploadProgress): string {
  switch (p.phase) {
    case 'theme':
      return 'Salvo tema…';
    case 'logo':
      return 'Carico logo…';
    case 'docs':
      return p.total > 0 ? `Carico documenti ${p.current + 1}/${p.total}…` : 'Carico documenti…';
    case 'done':
      return 'Completato';
    default:
      return 'Scaffolding…';
  }
}
