import { remaining, secondsTo, urgency } from '../lib/format';

// Window length (seconds) per milestone kind, used to fill the progress meter.
const WINDOWS: Record<string, number> = {
  early_warning: 24 * 3600,
  notification: 72 * 3600,
  initial_notification: 4 * 3600,
  intermediate_report: 72 * 3600,
  final_report: 30 * 86400,
};

export function DeadlineMeter({
  kind,
  dueAt,
  label,
}: {
  kind: string;
  dueAt: string;
  label: string;
}) {
  const secs = secondsTo(dueAt);
  const band = urgency(secs);
  const windowS = WINDOWS[kind] ?? 72 * 3600;
  const used = Math.max(0, Math.min(1, (windowS - secs) / windowS));
  return (
    <div className="dl">
      <div className="dl-top">
        <span>{label}</span>
        <span className={`dl-time ${band}`}>{remaining(dueAt)}</span>
      </div>
      <div className="dl-bar">
        <div className={`dl-fill ${band}`} style={{ width: `${Math.round(used * 100)}%` }} />
      </div>
    </div>
  );
}
