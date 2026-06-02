export function relTime(iso: string | null): string {
  if (!iso) return '—';
  const diff = (Date.now() - new Date(iso).getTime()) / 1000;
  if (diff < 60) return `${Math.floor(diff)}s ago`;
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return new Date(iso).toLocaleDateString();
}

export function joinLines(xs: string[]): string {
  return xs.join('\n');
}

export function splitLines(value: string): string[] {
  return value
    .split('\n')
    .map((x) => x.trim())
    .filter(Boolean);
}
