import { type ScanIntensity, type TargetKind } from '../../../lib/api';
import { Card, Icon } from '../../../components/ui';
import { scannersForTargetKind } from '../../../lib/scanners';
import { Field, SCANNERS_BY_INTENSITY } from './_shared';

export type ProfileStepProps = {
  kind: TargetKind | null;
  intensity: ScanIntensity;
  setIntensity: (v: ScanIntensity) => void;
  scanners: string[];
  setScanners: (cb: (cur: string[]) => string[]) => void;
  scheduleCron: string;
  setScheduleCron: (v: string) => void;
  resetScannersForIntensity: (i: ScanIntensity) => void;
};

export function ProfileStep(p: ProfileStepProps) {
  return (
    <Card title="Scan profile" subtitle="Defaults applied to every run against this target">
      <div className="space-y-5">
        <div>
          <label className="mb-2 block text-2xs font-mono uppercase tracking-wider text-text-muted">
            Default intensity
          </label>
          <div className="grid gap-2 sm:grid-cols-3">
            {(['passive', 'active', 'intrusive'] as ScanIntensity[]).map((i) => {
              const sel = p.intensity === i;
              return (
                <button
                  key={i}
                  type="button"
                  onClick={() => {
                    p.setIntensity(i);
                    p.resetScannersForIntensity(i);
                  }}
                  className={`flex items-center justify-between rounded-md border bg-bg-elevated p-3 text-left transition-colors ${
                    sel
                      ? 'border-brand/60 ring-1 ring-brand/30'
                      : 'border-bg-line hover:border-bg-line-strong'
                  }`}
                >
                  <span className="font-display text-sm font-medium capitalize text-text-primary">
                    {i}
                  </span>
                  {sel && <Icon.Check size={14} className="text-brand" />}
                </button>
              );
            })}
          </div>
          {p.intensity !== 'passive' && (
            <p className="mt-2 text-xs text-accent-warn">
              Active and intrusive scans require human-in-the-loop approval at run time.
            </p>
          )}
        </div>

        <div>
          <label className="mb-2 block text-2xs font-mono uppercase tracking-wider text-text-muted">
            Scanners
          </label>
          <div className="grid gap-2 sm:grid-cols-2">
            {(p.kind
              ? scannersForTargetKind(p.kind)
                  .filter((m) => m.intensities.includes(p.intensity))
                  .map((m) => m.id)
              : SCANNERS_BY_INTENSITY[p.intensity]
            ).map((s) => {
              const sel = p.scanners.includes(s);
              return (
                <label
                  key={s}
                  className={`flex cursor-pointer items-center gap-3 rounded-md border bg-bg-elevated px-3 py-2 transition-colors ${
                    sel ? 'border-brand/50' : 'border-bg-line hover:border-bg-line-strong'
                  }`}
                >
                  <input
                    type="checkbox"
                    checked={sel}
                    onChange={(e) =>
                      p.setScanners((cur) =>
                        e.target.checked
                          ? Array.from(new Set([...cur, s]))
                          : cur.filter((x) => x !== s)
                      )
                    }
                    className="accent-brand"
                  />
                  <span className="font-mono text-sm text-text-primary">{s}</span>
                </label>
              );
            })}
          </div>
        </div>

        <Field
          label="Schedule (cron, optional)"
          hint="Leave empty for on-demand only. Standard 5-field cron in UTC."
        >
          <input
            value={p.scheduleCron}
            onChange={(e) => p.setScheduleCron(e.target.value)}
            placeholder="0 2 * * *"
            className="ra-input font-mono"
          />
        </Field>
      </div>
    </Card>
  );
}
