import { Loader2, Palette, Save } from 'lucide-react';
import { useMemo, useState } from 'react';
import { toast } from 'sonner';
import { updateTenantTheme } from '../../../lib/api/admin';
import { Button } from '../../ui';
import { ColorField, HEX_RE, SubHeader } from './atoms';

const PALETTE_PRESETS = [
  { name: 'Steel', primary: '#1d4f91', hover: '#163a6c', accent: '#1f8a8a' },
  { name: 'Forest', primary: '#2f5d44', hover: '#234633', accent: '#b07c2e' },
  { name: 'Neutral', primary: '#3a4452', hover: '#2a323d', accent: '#5d7290' },
];

export interface ThemeInitial {
  primary: string;
  primary_hover: string;
  accent: string;
}

interface Props {
  tenant: string;
  initial: ThemeInitial;
  onSaved: (next: ThemeInitial) => void;
}

export function BrandingThemePanel({ tenant, initial, onSaved }: Props) {
  const [primary, setPrimary] = useState(initial.primary);
  const [primaryHover, setPrimaryHover] = useState(initial.primary_hover);
  const [accent, setAccent] = useState(initial.accent);
  const [busy, setBusy] = useState(false);

  const dirty = useMemo(
    () =>
      primary !== initial.primary ||
      primaryHover !== initial.primary_hover ||
      accent !== initial.accent,
    [primary, primaryHover, accent, initial]
  );

  const handleSave = async () => {
    for (const [k, v] of [
      ['primary', primary],
      ['primary_hover', primaryHover],
      ['accent', accent],
    ] as const) {
      if (v && !HEX_RE.test(v)) {
        toast.error(`${k}: usa hex #RRGGBB.`);
        return;
      }
    }
    setBusy(true);
    try {
      await updateTenantTheme(tenant, {
        primary: primary || undefined,
        primary_hover: primaryHover || undefined,
        accent: accent || undefined,
      });
      onSaved({ primary, primary_hover: primaryHover, accent });
      toast.success('Tema aggiornato.');
    } catch (e) {
      toast.error(`Tema fallito: ${(e as Error).message}`);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-3 rounded-md border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-3">
      <SubHeader title="Colori" icon={Palette} />
      <div className="grid grid-cols-3 gap-2">
        {PALETTE_PRESETS.map((p) => (
          <button
            key={p.name}
            type="button"
            onClick={() => {
              setPrimary(p.primary);
              setPrimaryHover(p.hover);
              setAccent(p.accent);
            }}
            className="focus-ring flex items-center justify-between rounded-md border border-[var(--color-border)] bg-[var(--color-canvas-raised)] px-2 py-1.5 text-left hover:bg-[var(--color-surface)]"
          >
            <span className="text-[10.5px] font-semibold text-ink">{p.name}</span>
            <span className="flex items-center gap-1" aria-hidden>
              {[p.primary, p.hover, p.accent].map((c) => (
                <span
                  key={c}
                  className="size-3 rounded-full border border-white/80 shadow-sm"
                  style={{ backgroundColor: c }}
                />
              ))}
            </span>
          </button>
        ))}
      </div>
      <div className="grid grid-cols-3 gap-2">
        <ColorField label="Primary" value={primary} onChange={setPrimary} />
        <ColorField label="Primary hover" value={primaryHover} onChange={setPrimaryHover} />
        <ColorField label="Accent" value={accent} onChange={setAccent} />
      </div>
      <div className="flex items-center justify-end">
        <Button
          variant="primary"
          onClick={handleSave}
          disabled={busy || !dirty}
          className="!text-[11px]"
        >
          {busy ? <Loader2 size={11} className="animate-spin" /> : <Save size={11} />}
          Salva colori
        </Button>
      </div>
    </div>
  );
}
