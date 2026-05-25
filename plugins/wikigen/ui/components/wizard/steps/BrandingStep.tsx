import { ImagePlus, Palette } from 'lucide-react';
import { toast } from 'sonner';
import { Callout, IconButton, SectionHeader } from '../../ui';
import { X } from 'lucide-react';
import type { StepProps } from '../atoms';
import { DEFAULT_FORM } from '../schema';

const PALETTE_PRESETS = [
  { name: 'Steel', primary: '#1d4f91', hover: '#163a6c', accent: '#1f8a8a' },
  { name: 'Forest', primary: '#2f5d44', hover: '#234633', accent: '#b07c2e' },
  { name: 'Neutral', primary: '#3a4452', hover: '#2a323d', accent: '#5d7290' },
];

export function BrandingStep({
  register,
  errors,
  values,
  setValue,
  logoFile,
  setLogoFile,
}: StepProps & {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  setValue: any;
  logoFile: File | null;
  setLogoFile: (f: File | null) => void;
}) {
  const v = values ?? DEFAULT_FORM;
  const onLogoPick = (f: File | null) => {
    if (!f) return;
    if (!/\.(svg|png|jpe?g|webp)$/i.test(f.name)) {
      toast.error('Estensione non ammessa. SVG, PNG, JPG, WEBP.');
      return;
    }
    if (f.size > 2 * 1024 * 1024) {
      toast.error('Logo > 2 MB. Comprimilo prima.');
      return;
    }
    setLogoFile(f);
  };
  return (
    <div className="space-y-5 px-5 py-4">
      <Callout tone="info" icon={Palette} title="Aspetto">
        Logo e colori sono facoltativi. Se non specificati, useremo il tema predefinito.
      </Callout>

      <section>
        <SectionHeader title="Logo" />
        <div className="flex items-center gap-3">
          <label
            className="focus-ring inline-flex cursor-pointer items-center gap-2 rounded-lg border border-dashed border-[var(--color-border)]
                       px-3 py-2 text-[11.5px] font-medium hover:border-[var(--color-brand-ring)] hover:bg-[var(--color-surface)]"
          >
            <input
              type="file"
              accept=".svg,.png,.jpg,.jpeg,.webp"
              hidden
              onChange={(e) => onLogoPick(e.target.files?.[0] ?? null)}
            />
            <ImagePlus size={14} className="text-[var(--color-brand)]" aria-hidden />
            {logoFile ? logoFile.name : 'Seleziona file · SVG, PNG, JPG, WEBP · max 2 MB'}
          </label>
          {logoFile && (
            <IconButton
              icon={X}
              aria-label="rimuovi logo"
              size="sm"
              onClick={() => setLogoFile(null)}
            />
          )}
        </div>
      </section>

      <section>
        <SectionHeader
          title="Colori"
          trailing={<span className="text-[10px] text-ink-subtle">Hex 6 cifre</span>}
        />
        <div className="mb-3 grid grid-cols-1 gap-2 sm:grid-cols-3">
          {PALETTE_PRESETS.map((p) => (
            <button
              key={p.name}
              type="button"
              onClick={() => {
                setValue('theme_primary', p.primary, { shouldDirty: true, shouldValidate: true });
                setValue('theme_primary_hover', p.hover, {
                  shouldDirty: true,
                  shouldValidate: true,
                });
                setValue('theme_accent', p.accent, { shouldDirty: true, shouldValidate: true });
              }}
              className="focus-ring flex items-center justify-between rounded-lg border border-[var(--color-border)] bg-[var(--color-canvas-raised)] px-3 py-2 text-left hover:bg-[var(--color-surface)]"
            >
              <span className="text-[11px] font-semibold text-ink">{p.name}</span>
              <span className="flex items-center gap-1" aria-hidden>
                {[p.primary, p.hover, p.accent].map((c) => (
                  <span
                    key={c}
                    className="size-4 rounded-full border border-white/80 shadow-sm"
                    style={{ backgroundColor: c }}
                  />
                ))}
              </span>
            </button>
          ))}
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <ColorField
            label="Primary"
            hint="Brand principale"
            value={v.theme_primary ?? ''}
            error={errors.theme_primary?.message}
            onChange={(c) =>
              setValue('theme_primary', c, { shouldDirty: true, shouldValidate: true })
            }
            register={register('theme_primary')}
          />
          <ColorField
            label="Primary hover"
            hint="Stato hover/active"
            value={v.theme_primary_hover ?? ''}
            error={errors.theme_primary_hover?.message}
            onChange={(c) =>
              setValue('theme_primary_hover', c, { shouldDirty: true, shouldValidate: true })
            }
            register={register('theme_primary_hover')}
          />
          <ColorField
            label="Accent"
            hint="Accenti / gradiente"
            value={v.theme_accent ?? ''}
            error={errors.theme_accent?.message}
            onChange={(c) =>
              setValue('theme_accent', c, { shouldDirty: true, shouldValidate: true })
            }
            register={register('theme_accent')}
          />
        </div>
        <p className="mt-1.5 text-[10.5px] leading-relaxed text-ink-subtle">
          Lascia vuoti i colori per usare quelli predefiniti.
        </p>
      </section>

      <section>
        <SectionHeader title="Anteprima" />
        <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-canvas-raised)] p-3">
          <div className="flex items-center justify-between gap-3 border-b border-[var(--color-border)] pb-3">
            <div className="flex min-w-0 items-center gap-2">
              <span
                className="grid size-8 shrink-0 place-items-center rounded-lg text-[13px] font-bold text-white"
                style={{ background: v.theme_primary || '#1d4f91' }}
              >
                {(v.label || v.name || 'W').charAt(0).toUpperCase()}
              </span>
              <div className="min-w-0">
                <div className="truncate text-[13px] font-semibold text-ink">
                  {v.label || v.name || 'Nuova wiki'}
                </div>
                <div className="text-[10px] text-ink-subtle">Enterprise knowledge base</div>
              </div>
            </div>
            <span
              className="h-7 rounded-md px-2.5 text-[11px] font-semibold leading-7 text-white"
              style={{ background: v.theme_primary_hover || v.theme_primary || '#1d4f91' }}
            >
              Cerca
            </span>
          </div>
          <div className="mt-3 grid grid-cols-3 gap-2">
            <div
              className="h-2 rounded-full"
              style={{ background: v.theme_primary || '#1d4f91' }}
            />
            <div
              className="h-2 rounded-full"
              style={{ background: v.theme_primary_hover || '#163a6c' }}
            />
            <div className="h-2 rounded-full" style={{ background: v.theme_accent || '#1f8a8a' }} />
          </div>
        </div>
      </section>
    </div>
  );
}

function ColorField({
  label,
  hint,
  value,
  error,
  onChange,
  register: registerProp,
}: {
  label: string;
  hint: string;
  value: string;
  error?: string;
  onChange: (v: string) => void;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  register: any;
}) {
  return (
    <div className="flex flex-col gap-1">
      <label className="text-[10.5px] font-semibold text-ink">{label}</label>
      <div className="flex items-center gap-2">
        <input
          type="color"
          value={value || '#003b5c'}
          onChange={(e) => onChange(e.target.value)}
          aria-label={`color picker ${label}`}
          className="size-9 rounded-md border border-[var(--color-border)] bg-transparent cursor-pointer"
        />
        <input
          {...registerProp}
          placeholder="#003b5c"
          className="input flex-1 font-mono text-[11.5px]"
          autoComplete="off"
          spellCheck={false}
        />
      </div>
      {error ? (
        <span className="text-[10px] text-[var(--color-danger)]">{error}</span>
      ) : (
        <span className="text-[10px] text-ink-subtle">{hint}</span>
      )}
    </div>
  );
}
