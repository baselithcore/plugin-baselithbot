export function formatDate(value?: string | null): string {
  if (!value) return '—';
  return new Date(value).toLocaleString('it-IT', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
}

export function truncateMiddle(value?: string | null, head = 8, tail = 6): string {
  if (!value) return '—';
  if (value.length <= head + tail + 3) return value;
  return `${value.slice(0, head)}...${value.slice(-tail)}`;
}

export function getErrorMessage(error: unknown, fallback = 'Errore inatteso.'): string {
  return error instanceof Error ? error.message : fallback;
}
