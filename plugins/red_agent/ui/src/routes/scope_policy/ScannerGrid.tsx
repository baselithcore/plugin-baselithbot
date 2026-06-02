import { Chip } from '../../components/ui';
import { KIND_LABEL, SCANNER_META, type ScannerKind } from '../../lib/scanners';

const KIND_TONE: Record<ScannerKind, 'brand' | 'warn' | 'critical' | 'good' | 'neutral'> = {
  recon: 'neutral',
  dast: 'warn',
  sast: 'brand',
  sca: 'brand',
  secret: 'critical',
  cspm: 'brand',
  iac: 'brand',
  k8s: 'brand',
  api: 'warn',
  config: 'neutral',
  threat_intel: 'good',
  tls: 'good',
  headers: 'good',
  sbom: 'brand',
  malware: 'critical',
};

export function ScannerGrid({
  allowed,
  enabled,
  onToggle,
}: {
  allowed: string[];
  enabled: string[];
  onToggle: (name: string, on: boolean) => void;
}) {
  const grouped = new Map<ScannerKind | 'unknown', string[]>();
  for (const name of allowed) {
    const meta = SCANNER_META[name];
    const kind = (meta?.kind ?? 'unknown') as ScannerKind | 'unknown';
    const list = grouped.get(kind) ?? [];
    list.push(name);
    grouped.set(kind, list);
  }
  const order: (ScannerKind | 'unknown')[] = [
    'recon',
    'dast',
    'sast',
    'sca',
    'secret',
    'sbom',
    'tls',
    'headers',
    'cspm',
    'iac',
    'k8s',
    'api',
    'config',
    'threat_intel',
    'unknown',
  ];

  return (
    <div className="space-y-4">
      {order
        .filter((k) => grouped.has(k))
        .map((kind) => (
          <div key={kind}>
            <div className="mb-2 flex items-center gap-2">
              <span className="text-2xs font-mono uppercase tracking-wider text-text-muted">
                {kind === 'unknown' ? 'Unknown' : KIND_LABEL[kind]}
              </span>
              <span className="text-2xs text-text-subtle">· {grouped.get(kind)!.length}</span>
            </div>
            <div className="flex flex-wrap gap-2">
              {grouped.get(kind)!.map((name) => {
                const meta = SCANNER_META[name];
                const sel = enabled.includes(name);
                return (
                  <label
                    key={name}
                    title={meta?.description ?? ''}
                    className={`flex cursor-pointer items-start gap-2 rounded-md border px-3 py-2 transition-colors ${
                      sel
                        ? 'border-brand/50 bg-brand/10'
                        : 'border-bg-line bg-bg-elevated hover:border-bg-line-strong'
                    }`}
                  >
                    <input
                      type="checkbox"
                      checked={sel}
                      onChange={(e) => onToggle(name, e.target.checked)}
                      className="mt-0.5 accent-brand"
                    />
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-sm text-text-primary">
                          {meta?.label ?? name}
                        </span>
                        {meta && <Chip tone={KIND_TONE[meta.kind]}>{KIND_LABEL[meta.kind]}</Chip>}
                      </div>
                      {meta && (
                        <p className="mt-0.5 max-w-[260px] truncate text-2xs text-text-muted">
                          {meta.description}
                        </p>
                      )}
                    </div>
                  </label>
                );
              })}
            </div>
          </div>
        ))}
    </div>
  );
}
