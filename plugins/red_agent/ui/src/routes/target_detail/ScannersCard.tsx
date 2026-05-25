import { useMemo, useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { api, type ScanIntensity, type TargetRecord } from '../../lib/api';
import { Button, Card, Chip, Icon } from '../../components/ui';
import { KIND_LABEL, scannersForTarget } from '../../lib/scanners';

const INTENSITIES: ScanIntensity[] = ['passive', 'active', 'intrusive'];

const INTENSITY_TONE: Record<ScanIntensity, string> = {
  passive: 'text-status-success ring-status-success/30 bg-status-success/10',
  active: 'text-accent-warn ring-accent-warn/30 bg-accent-warn/10',
  intrusive: 'text-sev-critical ring-sev-critical/30 bg-sev-critical/10',
};

function arraysEqual(a: string[], b: string[]): boolean {
  if (a.length !== b.length) return false;
  const sa = [...a].sort();
  const sb = [...b].sort();
  return sa.every((v, i) => v === sb[i]);
}

export function ScannersCard({ target }: { target: TargetRecord }) {
  const qc = useQueryClient();
  const compatible = useMemo(
    () => scannersForTarget(target.kind, target.value),
    [target.kind, target.value]
  );

  const initial = useMemo(() => {
    const raw = (target.profile?.scanners as unknown) ?? [];
    return Array.isArray(raw) ? (raw.filter((x) => typeof x === 'string') as string[]) : [];
  }, [target.profile]);

  const [enabled, setEnabled] = useState<string[]>(initial);

  const dirty = !arraysEqual(enabled, initial);

  const save = useMutation({
    mutationFn: () =>
      api.updateTarget(target.id, {
        profile: { ...(target.profile ?? {}), scanners: enabled },
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['target', target.id] });
    },
  });

  const toggle = (id: string) =>
    setEnabled((cur) =>
      cur.includes(id) ? cur.filter((x) => x !== id) : Array.from(new Set([...cur, id]))
    );

  const setAllByIntensity = (intensity: ScanIntensity, on: boolean) => {
    const ids = compatible.filter((s) => s.intensities.includes(intensity)).map((s) => s.id);
    setEnabled((cur) => {
      const set = new Set(cur);
      if (on) ids.forEach((id) => set.add(id));
      else ids.forEach((id) => set.delete(id));
      return Array.from(set);
    });
  };

  return (
    <Card
      title="Scanner toggles"
      action={
        <div className="flex items-center gap-2">
          {dirty && (
            <span className="text-2xs font-mono uppercase tracking-wider text-accent-warn">
              unsaved
            </span>
          )}
          <Button
            variant="secondary"
            onClick={() => setEnabled(initial)}
            disabled={!dirty || save.isPending}
          >
            Reset
          </Button>
          <Button
            variant="primary"
            onClick={() => save.mutate()}
            disabled={!dirty || save.isPending}
          >
            <Icon.Check size={14} />
            {save.isPending ? 'Saving…' : 'Save'}
          </Button>
        </div>
      }
    >
      <p className="mb-4 text-xs text-text-muted">
        Pick which scanners run against this target. Only adapters compatible with{' '}
        <span className="font-mono text-text-secondary">{target.kind}</span> targets are listed. The
        intensity tier of each run is still gated by Rules of Engagement.
      </p>

      <div className="space-y-5">
        {INTENSITIES.map((intensity) => {
          const items = compatible.filter((s) => s.intensities.includes(intensity));
          if (items.length === 0) return null;
          const allOn = items.every((s) => enabled.includes(s.id));
          const noneOn = items.every((s) => !enabled.includes(s.id));
          return (
            <section key={intensity}>
              <header className="mb-2 flex items-center justify-between">
                <span
                  className={`inline-flex items-center rounded px-2 py-0.5 text-2xs font-mono uppercase tracking-wider ring-1 ring-inset ${INTENSITY_TONE[intensity]}`}
                >
                  {intensity}
                </span>
                <div className="flex gap-1 text-2xs font-mono">
                  <button
                    type="button"
                    onClick={() => setAllByIntensity(intensity, true)}
                    disabled={allOn}
                    className="text-text-muted hover:text-brand disabled:opacity-30"
                  >
                    enable all
                  </button>
                  <span className="text-text-muted">·</span>
                  <button
                    type="button"
                    onClick={() => setAllByIntensity(intensity, false)}
                    disabled={noneOn}
                    className="text-text-muted hover:text-brand disabled:opacity-30"
                  >
                    disable all
                  </button>
                </div>
              </header>
              <div className="grid gap-2 sm:grid-cols-2">
                {items.map((s) => {
                  const on = enabled.includes(s.id);
                  return (
                    <label
                      key={s.id}
                      className={`flex cursor-pointer items-start gap-3 rounded-md border bg-bg-elevated px-3 py-2.5 transition-colors ${
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
            </section>
          );
        })}

        {compatible.length === 0 && (
          <p className="text-sm text-text-muted">
            No scanner adapters available for {target.kind} targets yet.
          </p>
        )}
      </div>
    </Card>
  );
}
