import { type ScanIntensity, type TargetKind } from '../../../lib/api';
import { Card, Chip } from '../../../components/ui';
import { KIND_META } from '../../../lib/targets';
import { ReviewRow } from './_shared';

export type ReviewStepProps = {
  kind: TargetKind | null;
  name: string;
  targetValue: string;
  environment: string;
  owner: string;
  intensity: ScanIntensity;
  scanners: string[];
  scheduleCron: string;
  error: unknown;
};

export function ReviewStep(p: ReviewStepProps) {
  return (
    <Card title="Review & create" subtitle="Verify the target before saving">
      <dl className="grid gap-4 sm:grid-cols-2">
        <ReviewRow label="Kind" value={p.kind ? KIND_META[p.kind].label : '—'} />
        <ReviewRow label="Name" value={p.name || p.targetValue} />
        <ReviewRow label="Value" value={p.targetValue} mono />
        <ReviewRow label="Environment" value={p.environment} />
        <ReviewRow label="Owner" value={p.owner || '—'} />
        <ReviewRow label="Default intensity" value={p.intensity} />
        <ReviewRow
          label="Scanners"
          value={
            <div className="flex flex-wrap gap-1">
              {p.scanners.map((s) => (
                <Chip key={s}>{s}</Chip>
              ))}
            </div>
          }
        />
        <ReviewRow label="Schedule" value={p.scheduleCron || 'on-demand'} mono />
      </dl>
      {p.error !== null && p.error !== undefined && (
        <p className="mt-4 rounded border border-sev-critical/40 bg-sev-critical/10 px-3 py-2 text-sm text-sev-critical">
          {String(p.error)}
        </p>
      )}
    </Card>
  );
}
