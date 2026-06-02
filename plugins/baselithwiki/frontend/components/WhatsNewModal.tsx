import { Sparkles } from 'lucide-react';
import { useEffect, useState } from 'react';
import { lastSeenVersion, markVersionSeen } from '../lib/onboarding';
import { Button, ModalShell } from './ui';

interface Entry {
  version: string;
  date: string;
  title: string;
  highlights: string[];
}

interface Manifest {
  entries: Entry[];
}

/**
 * Compare semver-ish strings (`a.b.c`). Returns >0 when `a` newer than `b`.
 * Bare numeric tuples; falls back to lexical when components are non-numeric.
 */
function cmpVersion(a: string, b: string): number {
  const pa = a.split('.');
  const pb = b.split('.');
  const len = Math.max(pa.length, pb.length);
  for (let i = 0; i < len; i++) {
    const na = Number(pa[i] ?? 0);
    const nb = Number(pb[i] ?? 0);
    if (Number.isNaN(na) || Number.isNaN(nb)) {
      const la = pa[i] ?? '';
      const lb = pb[i] ?? '';
      if (la !== lb) return la > lb ? 1 : -1;
      continue;
    }
    if (na !== nb) return na - nb;
  }
  return 0;
}

export function WhatsNewModal() {
  const [unseen, setUnseen] = useState<Entry[]>([]);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const r = await fetch('/whats_new.json', { cache: 'no-store' });
        if (!r.ok) return;
        const data = (await r.json()) as Manifest;
        if (cancelled) return;
        const seen = lastSeenVersion();
        const fresh = (data.entries ?? []).filter((e) => !seen || cmpVersion(e.version, seen) > 0);
        if (fresh.length === 0) {
          // Initial load on a brand-new install: silently mark latest seen so
          // existing users don't get spammed on first deploy of the modal.
          if (!seen && data.entries[0]) {
            markVersionSeen(data.entries[0].version);
          }
          return;
        }
        setUnseen(fresh);
        setOpen(true);
      } catch {
        /* ignore — feature is non-essential */
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const close = () => {
    if (unseen[0]) markVersionSeen(unseen[0].version);
    setOpen(false);
  };

  if (!open || unseen.length === 0) return null;

  return (
    <ModalShell open={open} onClose={close} title="Novità" icon={Sparkles} width="md">
      <div className="max-h-[70vh] overflow-y-auto px-5 py-4 space-y-5">
        {unseen.map((e) => (
          <section key={e.version}>
            <header className="mb-2 flex items-baseline justify-between gap-2">
              <h3 className="text-sm font-semibold text-ink">{e.title}</h3>
              <span className="text-[10px] uppercase text-ink-subtle font-mono">
                {e.version} · {e.date}
              </span>
            </header>
            <ul className="list-disc pl-5 space-y-1 text-[12px] text-ink-muted leading-relaxed">
              {e.highlights.map((h, i) => (
                <li key={i}>{h}</li>
              ))}
            </ul>
          </section>
        ))}
      </div>
      <div className="flex justify-end gap-2 border-t border-[var(--color-border)] px-5 py-3">
        <Button onClick={close}>Ho capito</Button>
      </div>
    </ModalShell>
  );
}
