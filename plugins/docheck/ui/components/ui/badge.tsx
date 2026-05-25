import { cn } from '@/lib/cn';
import type { Severity } from '@/lib/api';

const STYLES: Record<Severity, string> = {
  FAIL: 'bg-status-danger/15 text-status-danger border-status-danger/40',
  WARN: 'bg-status-warning/15 text-status-warning border-status-warning/40',
  PASS: 'bg-status-success/15 text-status-success border-status-success/40',
  INFO: 'bg-status-info/15 text-status-info border-status-info/40',
};

export function SeverityBadge({ severity, className }: { severity: Severity; className?: string }) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 px-2 h-[22px] text-xs font-medium rounded-full border',
        STYLES[severity],
        className
      )}
    >
      <span className="w-1.5 h-1.5 rounded-full bg-current" />
      {severity}
    </span>
  );
}
