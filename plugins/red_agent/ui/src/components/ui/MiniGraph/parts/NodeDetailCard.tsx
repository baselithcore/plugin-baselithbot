import type { SelectedNode } from '../types';

export function severityTone(sev?: string): string {
  switch (sev) {
    case 'critical':
      return '#ff3860';
    case 'high':
      return '#ff7a18';
    case 'medium':
      return '#ffb000';
    case 'low':
      return '#2dd4bf';
    case 'info':
      return '#4cc9f0';
    default:
      return '#6b7a90';
  }
}

export function NodeDetailCard({
  selected,
  onClose,
  onToggleCluster,
  isClusterExpanded,
}: {
  selected: SelectedNode;
  onClose: () => void;
  onToggleCluster: (id: string) => void;
  isClusterExpanded: boolean;
}) {
  const sevColor = severityTone(selected.severity);
  return (
    <div className="absolute right-3 top-3 z-10 w-[320px] max-w-[90%] overflow-hidden rounded-lg border border-bg-line bg-bg-base/95 shadow-xl backdrop-blur">
      <div
        className="flex items-center justify-between gap-2 border-b border-bg-line px-3 py-2"
        style={{
          background: `linear-gradient(90deg, ${selected.ring}24 0%, transparent 100%)`,
          borderLeftWidth: 3,
          borderLeftColor: selected.ring,
        }}
      >
        <span className="text-2xs font-mono uppercase tracking-wider text-text-muted">
          {selected.type}
          {selected.isCluster && selected.members ? ` · ${selected.members.length} items` : ''}
        </span>
        <button
          type="button"
          onClick={onClose}
          className="text-text-muted hover:text-text-primary"
          aria-label="Close"
        >
          ×
        </button>
      </div>
      <div className="px-3 py-2.5">
        <div className="mb-2 break-words text-sm font-medium text-text-primary">
          {selected.display}
        </div>
        <dl className="space-y-1.5 font-mono text-2xs">
          {selected.severity && (
            <div className="flex items-center justify-between gap-3">
              <dt className="text-text-muted">severity</dt>
              <dd
                className="rounded px-1.5 py-0.5 text-2xs uppercase"
                style={{ color: sevColor, background: `${sevColor}1f` }}
              >
                {selected.severity}
              </dd>
            </div>
          )}
          {selected.cvss !== undefined && selected.cvss !== '' && (
            <div className="flex items-center justify-between gap-3">
              <dt className="text-text-muted">cvss</dt>
              <dd className="text-text-primary">{String(selected.cvss)}</dd>
            </div>
          )}
          <div className="flex items-start justify-between gap-3">
            <dt className="text-text-muted">id</dt>
            <dd className="break-all text-right text-text-secondary">{selected.id}</dd>
          </div>
        </dl>
        {selected.isCluster && selected.members && (
          <div className="mt-3 space-y-2">
            <button
              type="button"
              onClick={() => onToggleCluster(selected.id)}
              className="ra-btn ra-btn-ghost ra-btn-sm w-full justify-center"
            >
              {isClusterExpanded ? 'Collapse cluster' : 'Expand cluster'}
            </button>
            <ul className="max-h-40 overflow-y-auto rounded border border-bg-line/60 bg-bg-base/50 p-1.5 font-mono text-2xs">
              {selected.members.map((m) => (
                <li
                  key={m.id}
                  className="flex items-center justify-between gap-2 rounded px-1.5 py-1 text-text-secondary hover:bg-bg-overlay"
                >
                  <span className="truncate">{m.display}</span>
                  {m.severity && (
                    <span
                      className="shrink-0 rounded px-1 text-2xs uppercase"
                      style={{
                        color: severityTone(m.severity),
                        background: `${severityTone(m.severity)}1f`,
                      }}
                    >
                      {m.severity}
                    </span>
                  )}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}
