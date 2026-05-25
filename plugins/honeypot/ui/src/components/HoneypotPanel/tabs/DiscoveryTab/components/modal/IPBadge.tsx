import { CopyButton } from './CopyButton';

interface IPBadgeProps {
  ip: string;
}

export function IPBadge({ ip }: IPBadgeProps) {
  return (
    <div className="ip-badge-wrapper">
      <code className="ip-badge">{ip}</code>
      <CopyButton text={ip} />
    </div>
  );
}
