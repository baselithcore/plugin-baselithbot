import { type ScanIntensity, type TargetKind } from '../../../lib/api';
import { Icon } from '../../../components/ui';
import { SCANNERS_BY_INTENSITY as REGISTRY_SCANNERS_BY_INTENSITY } from '../../../lib/scanners';

export const SCANNERS_BY_INTENSITY: Record<ScanIntensity, string[]> =
  REGISTRY_SCANNERS_BY_INTENSITY;

export const CLOUD_PROVIDERS = [
  { id: 'aws', label: 'AWS', accountField: 'Account ID', credField: 'IAM Role ARN' },
  { id: 'gcp', label: 'GCP', accountField: 'Project ID', credField: 'Service Account email' },
  {
    id: 'azure',
    label: 'Azure',
    accountField: 'Subscription ID',
    credField: 'App Registration ID',
  },
] as const;

export type CloudProvider = (typeof CLOUD_PROVIDERS)[number]['id'];

export function KindIcon({ k, size = 18 }: { k: TargetKind; size?: number }) {
  switch (k) {
    case 'web':
      return <Icon.Globe size={size} />;
    case 'cloud':
      return <Icon.Cloud size={size} />;
    case 'network':
      return <Icon.Network size={size} />;
    case 'host':
      return <Icon.Server size={size} />;
    case 'repo':
      return <Icon.Folder size={size} />;
    case 'binary':
      return <Icon.Bug size={size} />;
  }
}

export function Field({
  label,
  hint,
  children,
}: {
  label: string;
  hint?: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <label className="mb-1.5 block text-2xs font-mono uppercase tracking-wider text-text-muted">
        {label}
      </label>
      {children}
      {hint && <p className="mt-1 text-xs text-text-muted">{hint}</p>}
    </div>
  );
}

export function ReviewRow({
  label,
  value,
  mono,
}: {
  label: string;
  value: React.ReactNode;
  mono?: boolean;
}) {
  return (
    <div>
      <dt className="text-2xs font-mono uppercase tracking-wider text-text-muted">{label}</dt>
      <dd className={`mt-1 text-sm text-text-primary ${mono ? 'font-mono' : ''}`}>{value}</dd>
    </div>
  );
}
