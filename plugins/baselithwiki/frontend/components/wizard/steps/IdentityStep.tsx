import { AlertCircle, Building2, CheckCircle2, GitFork, Layers3 } from 'lucide-react';
import type { ScaffoldDefaults, TenantInfo } from '../../../lib/api';
import { Callout, SectionHeader } from '../../ui';
import { Field, type StepProps } from '../atoms';

export function IdentityStep({
  register,
  errors,
  defaults,
  tenants,
  activeTenant,
  onSelectExisting,
  onForkSeed,
  fromSeed,
  setFromSeed,
}: StepProps & {
  defaults: ScaffoldDefaults | null;
  tenants: TenantInfo[];
  activeTenant: string | null;
  onSelectExisting: (name: string) => void;
  onForkSeed: (name: string) => void;
  fromSeed: string;
  setFromSeed: (slug: string) => void;
}) {
  const userPacks = tenants.filter((t) => !t.is_seed);
  const seeds = tenants.filter((t) => t.is_seed);

  return (
    <div className="space-y-5 px-5 py-4">
      <Callout tone="info" icon={Building2} title="Identità del dominio">
        Scegli un identificativo stabile e un nome leggibile. Se vuoi, parti da un esempio
        precompilato.
      </Callout>

      {userPacks.length > 0 && (
        <section>
          <SectionHeader title={`Le tue wiki (${userPacks.length})`} />
          <div className="rounded-lg border border-[var(--color-border)] divide-y divide-[var(--color-border)]">
            {userPacks.map((t) => (
              <button
                key={t.name}
                onClick={() => onSelectExisting(t.name)}
                className="focus-ring flex w-full items-center justify-between gap-3 px-3 py-2 text-left hover:bg-[var(--color-surface)]"
              >
                <div className="min-w-0">
                  <div className="truncate text-[12px] font-medium">
                    {t.label}
                    {t.is_active && (
                      <span className="ml-2 inline-flex items-center gap-1 rounded-full bg-[var(--color-success)]/15 px-1.5 py-px text-[9px] uppercase text-[var(--color-success)]">
                        <CheckCircle2 size={9} aria-hidden />
                        attiva
                      </span>
                    )}
                  </div>
                  <div className="truncate text-[10.5px] text-ink-subtle">
                    {t.language.toUpperCase()} · {t.page_types.length} tipi di pagina
                  </div>
                </div>
                {!t.is_active && t.valid && (
                  <span className="whitespace-nowrap text-[10px] text-ink-muted">attiva →</span>
                )}
                {!t.valid && (
                  <AlertCircle
                    size={12}
                    className="shrink-0 text-[var(--color-danger)]"
                    aria-label="configurazione non valida"
                  />
                )}
              </button>
            ))}
          </div>
          <p className="mt-2 text-[10.5px] leading-relaxed text-ink-subtle">
            Selezionare una wiki la imposta come attiva al prossimo avvio.
            {activeTenant && (
              <>
                {' '}
                Attualmente attiva: <strong className="text-ink">{activeTenant}</strong>.
              </>
            )}
          </p>
        </section>
      )}

      {seeds.length > 0 && (
        <section>
          <SectionHeader title={`Esempi pronti (${seeds.length})`} />
          <div className="rounded-lg border border-[var(--color-border)] divide-y divide-[var(--color-border)]">
            {seeds.map((t) => (
              <div key={t.name} className="flex items-center justify-between gap-3 px-3 py-2">
                <div className="min-w-0">
                  <div className="flex items-center gap-1.5 truncate text-[12px] font-medium">
                    {t.label}
                    <span className="inline-flex items-center gap-1 rounded-full bg-[var(--color-brand-soft)] px-1.5 py-px text-[9px] uppercase text-[var(--color-brand-contrast)]">
                      <Layers3 size={9} aria-hidden />
                      esempio
                    </span>
                    {fromSeed === t.name && (
                      <span className="rounded-full bg-[var(--color-success)]/15 px-1.5 py-px text-[9px] uppercase text-[var(--color-success)]">
                        in fork
                      </span>
                    )}
                  </div>
                  <div className="truncate text-[10.5px] text-ink-subtle">
                    {t.language.toUpperCase()} · {t.page_types.length} tipi di pagina
                  </div>
                  <div className="mt-0.5 truncate text-[10.5px] text-ink-muted">
                    {t.description}
                  </div>
                </div>
                <button
                  onClick={() => onForkSeed(t.name)}
                  className="focus-ring inline-flex shrink-0 items-center gap-1 rounded-md border border-[var(--color-brand)] px-2 py-1 text-[10.5px] font-semibold text-[var(--color-brand)] hover:bg-[var(--color-brand-soft)]"
                  title={`Crea una copia personalizzabile partendo da ${t.label}`}
                >
                  <GitFork size={11} aria-hidden />
                  Duplica
                </button>
              </div>
            ))}
          </div>
          <p className="mt-2 text-[10.5px] leading-relaxed text-ink-subtle">
            Gli esempi non sono attivabili direttamente: duplicane uno per personalizzarne testi,
            tipi di pagina e regole.
          </p>
        </section>
      )}

      <section>
        <SectionHeader
          title={fromSeed ? `Duplicazione da ${fromSeed}` : 'Crea nuova wiki'}
          trailing={
            fromSeed && (
              <button
                onClick={() => setFromSeed('')}
                className="focus-ring rounded text-[10px] font-medium text-ink-muted hover:text-ink"
              >
                Annulla duplicazione
              </button>
            )
          }
        />
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <Field
            label="Identificativo *"
            hint="Lettere minuscole, cifre e trattini. Es. legal-it."
            error={errors.name?.message}
          >
            <input
              {...register('name')}
              placeholder="legal"
              className="input"
              autoComplete="off"
              spellCheck={false}
            />
          </Field>
          <Field
            label="Lingua"
            hint="Codice ISO della lingua principale dei documenti."
            error={errors.language?.message}
          >
            <select {...register('language')} className="input">
              {(defaults?.languages ?? ['it', 'en']).map((l) => (
                <option key={l} value={l}>
                  {l}
                </option>
              ))}
            </select>
          </Field>
          <Field
            label="Nome visualizzato"
            hint="Compare nelle interfacce. Lascia vuoto per derivarlo dall'identificativo."
            error={errors.label?.message}
            full
          >
            <input
              {...register('label')}
              placeholder="Wiki Legale"
              className="input"
              autoComplete="off"
            />
          </Field>
          <Field
            label="Descrizione"
            hint="Una riga, visibile in homepage."
            error={errors.description?.message}
            full
          >
            <textarea
              {...register('description')}
              placeholder="Sentenze, normative e contrattualistica del team Legal."
              rows={2}
              className="input resize-y"
            />
          </Field>
        </div>
      </section>

      {defaults && (
        <Callout tone="neutral" icon={null} title="Tipi di pagina inclusi">
          <div className="mt-1 flex flex-wrap gap-1">
            {defaults.suggested_page_types.map((p) => (
              <span key={p.id} className="chip text-[10px]">
                {p.id}
              </span>
            ))}
          </div>
          <p className="mt-1.5 text-[10.5px] leading-relaxed text-ink-subtle">
            Potrai personalizzarli dopo la creazione della wiki.
          </p>
        </Callout>
      )}
    </div>
  );
}
