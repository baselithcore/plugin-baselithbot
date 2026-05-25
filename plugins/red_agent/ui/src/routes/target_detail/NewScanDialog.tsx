import { useEffect, useMemo, useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { api, type ScanIntensity, type TargetRecord } from '../../lib/api';
import { Button, Chip, Icon, Modal } from '../../components/ui';
import { KIND_LABEL, scannersForTarget } from '../../lib/scanners';

const INTENSITIES: ScanIntensity[] = ['passive', 'active', 'intrusive'];

const INTENSITY_TONE: Record<ScanIntensity, string> = {
  passive: 'border-status-success/40 bg-status-success/10 text-status-success',
  active: 'border-accent-warn/40 bg-accent-warn/10 text-accent-warn',
  intrusive: 'border-sev-critical/40 bg-sev-critical/10 text-sev-critical',
};

const INTENSITY_HINT: Record<ScanIntensity, string> = {
  passive: 'Read-only signals. No traffic to the target outside fingerprinting.',
  active: 'Sends probes. Requires HITL approval per Rules of Engagement.',
  intrusive: 'Exploit primitives fire. HITL gated. Use only inside intrusive window.',
};

export function NewScanDialog({
  open,
  onClose,
  target,
}: {
  open: boolean;
  onClose: () => void;
  target: TargetRecord;
}) {
  const nav = useNavigate();
  const qc = useQueryClient();

  const compatible = useMemo(
    () => scannersForTarget(target.kind, target.value),
    [target.kind, target.value]
  );

  const profileScanners = useMemo(() => {
    const raw = (target.profile?.scanners as unknown) ?? [];
    return Array.isArray(raw) ? (raw.filter((x) => typeof x === 'string') as string[]) : [];
  }, [target.profile]);

  const profileIntensity = useMemo<ScanIntensity>(() => {
    const v = target.profile?.intensity as unknown;
    return v === 'active' || v === 'intrusive' ? v : 'passive';
  }, [target.profile]);

  const [intensity, setIntensity] = useState<ScanIntensity>(profileIntensity);
  const [scanners, setScanners] = useState<string[]>(profileScanners);
  const [notes, setNotes] = useState('');

  useEffect(() => {
    if (open) {
      setIntensity(profileIntensity);
      setScanners(profileScanners);
      setNotes('');
    }
  }, [open, profileIntensity, profileScanners]);

  const launch = useMutation({
    mutationFn: () =>
      api.launchTargetScan(target.id, {
        scanners,
        intensity,
        notes: notes.trim() || undefined,
      }),
    onSuccess: (r) => {
      qc.invalidateQueries({ queryKey: ['target-runs', target.id] });
      onClose();
      nav(`/scans/${r.scan_id}`);
    },
  });

  const tierItems = compatible.filter((s) => s.intensities.includes(intensity));
  const incompatibleSelected = scanners.filter((id) => !tierItems.some((s) => s.id === id));

  const toggle = (id: string) =>
    setScanners((cur) =>
      cur.includes(id) ? cur.filter((x) => x !== id) : Array.from(new Set([...cur, id]))
    );

  const allOn = tierItems.length > 0 && tierItems.every((s) => scanners.includes(s.id));
  const noneOn = tierItems.every((s) => !scanners.includes(s.id));

  const setAll = (on: boolean) =>
    setScanners((cur) => {
      const set = new Set(cur);
      tierItems.forEach((s) => (on ? set.add(s.id) : set.delete(s.id)));
      return Array.from(set);
    });

  const canLaunch = scanners.length > 0 && !launch.isPending;

  return (
    <Modal open={open} onClose={onClose} size="lg" ariaLabel="New scan">
      <div className="rounded-lg border border-bg-line bg-bg-elevated">
        <header className="flex items-start justify-between gap-4 border-b border-bg-line px-5 py-4">
          <div>
            <h2 className="font-display text-lg font-medium text-text-primary">New scan</h2>
            <p className="mt-1 text-xs text-text-muted">
              Launch a one-off scan against{' '}
              <span className="font-mono text-text-secondary">{target.name}</span>. Overrides do not
              mutate the target's stored profile.
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close"
            className="grid h-7 w-7 place-items-center rounded text-text-muted hover:bg-bg-hover hover:text-text-primary"
          >
            <Icon.X size={14} />
          </button>
        </header>

        <div className="space-y-5 px-5 py-4">
          <div>
            <label className="mb-2 block text-2xs font-mono uppercase tracking-wider text-text-muted">
              Intensity
            </label>
            <div className="grid grid-cols-3 gap-2">
              {INTENSITIES.map((i) => {
                const sel = intensity === i;
                return (
                  <button
                    key={i}
                    type="button"
                    onClick={() => setIntensity(i)}
                    className={`rounded-md border px-3 py-2 text-left transition-colors ${
                      sel
                        ? INTENSITY_TONE[i]
                        : 'border-bg-line bg-bg-base text-text-secondary hover:border-bg-line-strong'
                    }`}
                  >
                    <div className="font-mono text-xs uppercase tracking-wider">{i}</div>
                  </button>
                );
              })}
            </div>
            <p className="mt-2 text-xs text-text-muted">{INTENSITY_HINT[intensity]}</p>
          </div>

          <div>
            <div className="mb-2 flex items-center justify-between">
              <label className="text-2xs font-mono uppercase tracking-wider text-text-muted">
                Scanners ({scanners.length} selected)
              </label>
              <div className="flex gap-1 text-2xs font-mono">
                <button
                  type="button"
                  onClick={() => setAll(true)}
                  disabled={allOn}
                  className="text-text-muted hover:text-brand disabled:opacity-30"
                >
                  enable all
                </button>
                <span className="text-text-muted">·</span>
                <button
                  type="button"
                  onClick={() => setAll(false)}
                  disabled={noneOn}
                  className="text-text-muted hover:text-brand disabled:opacity-30"
                >
                  disable all
                </button>
              </div>
            </div>
            {tierItems.length === 0 ? (
              <p className="rounded-md border border-bg-line bg-bg-base px-3 py-3 text-sm text-text-muted">
                No scanners available for {target.kind} at intensity{' '}
                <span className="font-mono">{intensity}</span>.
              </p>
            ) : (
              <div className="grid gap-2 sm:grid-cols-2">
                {tierItems.map((s) => {
                  const on = scanners.includes(s.id);
                  return (
                    <label
                      key={s.id}
                      className={`flex cursor-pointer items-start gap-3 rounded-md border bg-bg-base px-3 py-2.5 transition-colors ${
                        on ? 'border-brand/50' : 'border-bg-line hover:border-bg-line-strong'
                      }`}
                    >
                      <input
                        type="checkbox"
                        checked={on}
                        onChange={() => toggle(s.id)}
                        className="mt-0.5 accent-brand"
                      />
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-2">
                          <span className="font-mono text-sm text-text-primary">{s.label}</span>
                          <Chip>{KIND_LABEL[s.kind]}</Chip>
                        </div>
                        <p className="mt-0.5 text-xs text-text-muted">{s.description}</p>
                      </div>
                    </label>
                  );
                })}
              </div>
            )}
            {incompatibleSelected.length > 0 && (
              <p className="mt-2 text-2xs font-mono text-accent-warn">
                {incompatibleSelected.length} scanner(s) not compatible with this intensity will be
                skipped: {incompatibleSelected.join(', ')}
              </p>
            )}
          </div>

          <div>
            <label className="mb-2 block text-2xs font-mono uppercase tracking-wider text-text-muted">
              Notes (optional)
            </label>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              rows={2}
              placeholder="Why this run? Stays attached to the audit trail."
              className="ra-input w-full font-mono text-sm"
            />
          </div>

          {launch.error && (
            <p className="rounded border border-sev-critical/40 bg-sev-critical/10 px-3 py-2 text-sm text-sev-critical">
              {String(launch.error)}
            </p>
          )}
        </div>

        <footer className="flex items-center justify-end gap-2 border-t border-bg-line px-5 py-3">
          <Button variant="ghost" onClick={onClose} disabled={launch.isPending}>
            Cancel
          </Button>
          <Button variant="primary" onClick={() => launch.mutate()} disabled={!canLaunch}>
            <Icon.Bolt size={14} />
            {launch.isPending ? 'Launching…' : 'Launch scan'}
          </Button>
        </footer>
      </div>
    </Modal>
  );
}
