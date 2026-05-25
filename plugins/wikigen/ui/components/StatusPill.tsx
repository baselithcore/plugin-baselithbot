import { useEffect, useState } from 'react';
import { AlertCircle, Cpu, Loader2 } from 'lucide-react';
import { fetchStatus } from '../lib/api';
import type { Status } from '../lib/types';
import { cn } from '../lib/cn';

type State = 'loading' | 'ok' | 'degraded' | 'error';

export function StatusPill({ compact = false }: { compact?: boolean }) {
  const [status, setStatus] = useState<Status | null>(null);
  const [state, setState] = useState<State>('loading');

  useEffect(() => {
    const ctrl = new AbortController();
    fetchStatus(ctrl.signal)
      .then((s) => {
        setStatus(s);
        const ok = s.qdrant.available && s.embedder.name;
        setState(ok ? 'ok' : 'degraded');
      })
      .catch(() => setState('error'));
    return () => ctrl.abort();
  }, []);

  const dotColor =
    state === 'error'
      ? 'var(--color-danger)'
      : state === 'degraded'
        ? 'var(--color-warning)'
        : state === 'ok'
          ? 'var(--color-success)'
          : 'var(--color-ink-subtle)';

  const label =
    state === 'loading'
      ? 'connessione'
      : state === 'error'
        ? 'offline'
        : state === 'degraded'
          ? 'degradato'
          : status
            ? status.provider.model
            : 'ok';

  const subLabel = status?.provider.vendor ?? 'backend';

  const tooltip = status
    ? [
        `${status.provider.vendor} · ${status.provider.model}`,
        status.embedder.name
          ? `embedder: ${status.embedder.name} (dim ${status.embedder.dim})`
          : 'embedder: —',
        `qdrant: ${status.qdrant.mode} · ${status.qdrant.points ?? 0} pts`,
        status.graph.enabled
          ? `graph: ${status.graph.nodes ?? 0} nodi / ${status.graph.edges ?? 0} archi`
          : 'graph: disattivo',
        `vault: ${status.vault.pages} pagine`,
      ].join('\n')
    : 'backend non raggiungibile';

  if (compact) {
    return (
      <div
        className={cn(
          'inline-flex size-9 items-center justify-center rounded-lg border',
          'border-[var(--color-border)] bg-[var(--color-canvas-raised)] shadow-[var(--shadow-xs)]',
          'hover:border-[var(--color-border-strong)] transition-colors'
        )}
        title={tooltip}
        aria-label={`stato backend: ${label}`}
      >
        {state === 'loading' ? (
          <Loader2 size={12} className="animate-spin text-ink-subtle" aria-hidden />
        ) : state === 'error' ? (
          <AlertCircle size={12} className="text-[var(--color-danger)]" aria-hidden />
        ) : (
          <span
            className="status-dot"
            style={{ background: dotColor, width: 8, height: 8, borderRadius: 9999 }}
            aria-hidden
          />
        )}
      </div>
    );
  }

  return (
    <div
      className={cn(
        'group inline-flex items-center gap-2 rounded-full pl-2 pr-2.5 py-1 text-xs',
        'bg-[var(--color-canvas-raised)] border border-[var(--color-border)]',
        'font-medium tabular-nums hover:border-[var(--color-border-strong)] transition-colors'
      )}
      title={tooltip}
    >
      {state === 'loading' ? (
        <Loader2 size={11} className="animate-spin text-ink-subtle" />
      ) : state === 'error' ? (
        <AlertCircle size={11} className="text-[var(--color-danger)]" />
      ) : (
        <span className="inline-flex items-center" style={{ color: dotColor }}>
          <span className="status-dot" style={{ background: dotColor }} />
        </span>
      )}
      <span className="text-ink-subtle">{subLabel}</span>
      <span className="text-ink-subtle">·</span>
      <span className="flex items-center gap-1 text-ink">
        <Cpu size={10} className="text-ink-subtle" />
        {label}
      </span>
    </div>
  );
}
