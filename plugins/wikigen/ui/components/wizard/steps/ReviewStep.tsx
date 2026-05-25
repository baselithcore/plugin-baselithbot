import { CheckCircle2, FileCode2, Info, Loader2, Sparkles } from 'lucide-react';
import type { UseFormRegister } from 'react-hook-form';
import type { ScaffoldPlanResponse } from '../../../lib/api';
import { cn } from '../../../lib/cn';
import { Callout, SectionHeader } from '../../ui';
import { Row } from '../atoms';
import { shorten } from '../helpers';
import type { WizardForm } from '../schema';

export function ReviewStep({
  plan,
  planLoading,
  planError,
  register,
  synthesizePrompts,
  fromSeed,
}: {
  plan: ScaffoldPlanResponse | null;
  planLoading: boolean;
  planError: string | null;
  register: UseFormRegister<WizardForm>;
  synthesizePrompts: boolean;
  fromSeed: string;
}) {
  if (planLoading)
    return (
      <div className="grid place-items-center px-5 py-10 text-ink-subtle">
        <Loader2 size={16} className="animate-spin" aria-hidden />
      </div>
    );
  if (planError)
    return (
      <div className="px-5 py-6">
        <Callout tone="danger">{planError}</Callout>
      </div>
    );
  if (!plan) return null;

  return (
    <div className="space-y-4 px-5 py-4">
      <Callout tone="success" icon={CheckCircle2} title={plan.label}>
        {plan.description}
        <dl className="mt-2 grid grid-cols-2 gap-x-4 gap-y-1 text-[10.5px] font-mono text-ink">
          <Row k="identificativo" v={plan.name} />
          <Row k="lingua" v={plan.language} />
          <Row k="cartella pack" v={shorten(plan.target_pack_dir)} />
          <Row k="vault" v={shorten(plan.vault_path)} />
        </dl>
        {plan.pack_dir_exists && (
          <div className="mt-2 text-[10.5px] text-[var(--color-warning)]">
            La cartella esiste già — l'applicazione fallirà a meno di abilitare la sovrascrittura.
          </div>
        )}
      </Callout>

      <section>
        <SectionHeader title="Cosa verrà creato" icon={FileCode2} />
        <ul className="rounded-lg border border-[var(--color-border)] divide-y divide-[var(--color-border)]">
          {plan.operations.map((op, i) => (
            <li
              key={i}
              className="flex items-center gap-2 px-3 py-1.5 font-mono text-[11px] text-ink"
            >
              <OpKindBadge kind={op.kind} />
              <span className="truncate">{shorten(op.target)}</span>
              {op.note && (
                <span className="ml-auto text-[10px] text-ink-subtle">{op.note}</span>
              )}
            </li>
          ))}
        </ul>
      </section>

      {plan.env_diff.length > 0 && (
        <details className="group rounded-lg border border-[var(--color-border)]">
          <summary className="cursor-pointer list-none px-3 py-2 text-[10.5px] font-semibold uppercase text-ink-subtle flex items-center gap-1.5">
            <span>Configurazione persistita</span>
            <span className="ml-auto text-[10px] font-normal normal-case text-ink-subtle group-open:hidden">
              mostra
            </span>
            <span className="ml-auto hidden text-[10px] font-normal normal-case text-ink-subtle group-open:inline">
              nascondi
            </span>
          </summary>
          <pre className="border-t border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2 text-[11px] font-mono whitespace-pre-wrap break-all">
            {plan.env_diff
              .map((d) => `+ ${d.key}=${d.value === '***' ? '<chiave protetta>' : d.value}`)
              .join('\n')}
          </pre>
        </details>
      )}

      <SynthesisToggle
        register={register}
        synthesizePrompts={synthesizePrompts}
        fromSeed={fromSeed}
      />

      <Callout tone="info" icon={Info} title="Cosa succede dopo">
        <ol className="mt-1 list-decimal list-inside space-y-0.5 text-[11px] text-ink-muted">
          {plan.next_steps.map((s, i) => (
            <li key={i}>{s}</li>
          ))}
        </ol>
      </Callout>
    </div>
  );
}

function SynthesisToggle({
  register,
  synthesizePrompts,
  fromSeed,
}: {
  register: UseFormRegister<WizardForm>;
  synthesizePrompts: boolean;
  fromSeed: string;
}) {
  // Synthesis is skipped for forks: a curated seed already ships
  // domain-tuned prompts. Show the toggle as disabled + explain why.
  const disabled = !!fromSeed;
  return (
    <section className="rounded-lg border border-[var(--color-border)] px-3 py-3">
      <label
        className={cn(
          'flex items-start gap-2.5 text-[11.5px] leading-relaxed',
          disabled && 'opacity-60'
        )}
      >
        <input
          type="checkbox"
          {...register('synthesize_prompts')}
          disabled={disabled}
          className="mt-0.5 h-3.5 w-3.5 cursor-pointer rounded border-[var(--color-border)] accent-[var(--color-brand)]"
        />
        <span className="flex-1">
          <span className="flex items-center gap-1.5 font-semibold text-ink">
            <Sparkles size={12} className="text-[var(--color-brand)]" aria-hidden />
            Personalizza il prompt sul dominio
          </span>
          <span className="mt-0.5 block text-[10.5px] text-ink-subtle">
            {disabled ? (
              <>
                Disabilitato per i fork da esempio: il pack <strong>{fromSeed}</strong> ha
                già un prompt curato per il suo dominio.
              </>
            ) : synthesizePrompts ? (
              <>
                All'apply il provider configurato genererà uno <em>system prompt</em>
                tarato sul dominio scelto (slot, gerarchie di fonti, pairing,
                disclaimer) invece dello scheletro generico. Aggiunge ~5-15s al
                processo di creazione. In caso di errore si torna al template.
              </>
            ) : (
              <>
                Verrà usato lo scheletro generico di <code>_template</code>: i
                segnaposto andranno riempiti a mano in{' '}
                <code>domains/&lt;nome&gt;/prompts/system.j2</code>.
              </>
            )}
          </span>
        </span>
      </label>
    </section>
  );
}

function OpKindBadge({ kind }: { kind: string }) {
  const cls =
    kind === 'remove'
      ? 'bg-[var(--color-danger)]/15 text-[var(--color-danger)]'
      : 'bg-[var(--color-brand-soft)] text-[var(--color-brand-contrast)]';
  return (
    <span className={cn('shrink-0 rounded px-1.5 text-[9px] uppercase font-semibold', cls)}>
      {kind === 'remove' ? 'rimuovi' : kind === 'create' ? 'crea' : kind}
    </span>
  );
}
