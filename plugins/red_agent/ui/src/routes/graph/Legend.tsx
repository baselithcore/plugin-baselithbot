import { NODE_BORDER, EDGE_COLOR } from './styles';

const NODE_KEYS: string[] = [
  'Target',
  'CloudResource',
  'Endpoint',
  'Service',
  'Vulnerability',
  'Identity',
  'DataStore',
  'Scan',
  'CVE',
  'CWE',
];
const EDGE_KEYS: string[] = [
  'HAS_VULN',
  'HAS_ENDPOINT',
  'EXPOSES',
  'SCANNED_BY',
  'FOUND',
  'LATERAL_TO',
  'MAPS_TO',
  'GOVERNED_BY',
];

export function Legend({ visible, onToggle }: { visible: boolean; onToggle: () => void }) {
  return (
    <div
      className="absolute bottom-4 right-4 z-20 max-w-[260px] rounded-lg border border-bg-line bg-bg-elevated/95 p-3 shadow-elevated backdrop-blur"
      role="region"
      aria-label="legend"
    >
      <button
        type="button"
        onClick={onToggle}
        className="flex w-full items-center justify-between font-display text-xs text-text-muted transition hover:text-text-primary focus:outline-none focus-visible:ring-2 focus-visible:ring-brand/40"
        aria-expanded={visible}
      >
        <span>Legend</span>
        <span aria-hidden>{visible ? '▾' : '▸'}</span>
      </button>
      {visible && (
        <div className="mt-3 space-y-3">
          <Group title="Nodes">
            {NODE_KEYS.map((k) => (
              <li key={k} className="flex items-center gap-2 text-xs">
                <span
                  className="inline-block h-2.5 w-2.5 rounded-sm border"
                  style={{
                    background: NODE_BORDER[k],
                    borderColor: NODE_BORDER[k],
                    boxShadow: `0 0 6px ${NODE_BORDER[k]}`,
                  }}
                />
                <span className="text-text-primary">{k}</span>
              </li>
            ))}
          </Group>
          <Group title="Edges">
            {EDGE_KEYS.map((k) => (
              <li key={k} className="flex items-center gap-2 text-xs">
                <span
                  className="inline-block h-0.5 w-5 rounded"
                  style={{ background: EDGE_COLOR[k] }}
                />
                <span className="font-display text-text-primary">{k}</span>
              </li>
            ))}
          </Group>
          <Group title="States">
            <li className="flex items-center gap-2 text-xs">
              <span
                className="inline-block h-2.5 w-2.5 rounded border-2"
                style={{ borderColor: '#00ffd1' }}
              />
              <span className="text-text-primary">selected</span>
            </li>
            <li className="flex items-center gap-2 text-xs">
              <span
                className="inline-block h-2.5 w-2.5 rounded border-2"
                style={{ borderColor: '#ffb000' }}
              />
              <span className="text-text-primary">path to target</span>
            </li>
          </Group>
        </div>
      )}
    </div>
  );
}

function Group({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div>
      <p className="font-display text-[10px] uppercase tracking-wider text-text-muted">{title}</p>
      <ul className="mt-1.5 space-y-1">{children}</ul>
    </div>
  );
}
