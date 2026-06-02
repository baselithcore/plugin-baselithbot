import { Loader2, Save } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import { toast } from 'sonner';
import {
  type TenantBrandingPayload,
  type TenantBrandingUpdateBody,
  type TenantSuggestedQuestion,
  fetchTenantBranding,
  updateTenantBranding,
} from '../../lib/api/admin';
import { useDomain } from '../../contexts/DomainContext';
import { Button } from '../ui';
import { BrandingInputStyle, Field, SubHeader } from './branding/atoms';
import { BrandingLogoPanel } from './branding/BrandingLogoPanel';
import { BrandingQuestionsEditor } from './branding/BrandingQuestionsEditor';
import { BrandingThemePanel, type ThemeInitial } from './branding/BrandingThemePanel';

interface Props {
  tenant: string;
}

interface BrandingFormState {
  label: string;
  description: string;
  app_name: string;
  short_name: string;
  vault_label: string;
  tagline: string;
  hero_question: string;
  hero_highlight: string;
  hero_pill: string;
  hero_pill_icon: string;
  empty_state: string;
  disclaimer: string;
}

const EMPTY_FORM: BrandingFormState = {
  label: '',
  description: '',
  app_name: '',
  short_name: '',
  vault_label: '',
  tagline: '',
  hero_question: '',
  hero_highlight: '',
  hero_pill: '',
  hero_pill_icon: '',
  empty_state: '',
  disclaimer: '',
};

function readForm(p: TenantBrandingPayload): BrandingFormState {
  const ui = p.ui ?? {};
  return {
    label: p.label ?? '',
    description: p.description ?? '',
    app_name: (ui.app_name as string | undefined) ?? '',
    short_name: (ui.short_name as string | undefined) ?? '',
    vault_label: (ui.vault_label as string | undefined) ?? '',
    tagline: (ui.tagline as string | undefined) ?? '',
    hero_question: (ui.hero_question as string | undefined) ?? '',
    hero_highlight: (ui.hero_highlight as string | undefined) ?? '',
    hero_pill: (ui.hero_pill as string | undefined) ?? '',
    hero_pill_icon: (ui.hero_pill_icon as string | undefined) ?? '',
    empty_state: (ui.empty_state as string | undefined) ?? '',
    disclaimer: (ui.disclaimer as string | undefined) ?? '',
  };
}

function readQuestions(p: TenantBrandingPayload): TenantSuggestedQuestion[] {
  return (p.ui?.suggested_questions ?? []).map((q) => ({
    label: q.label ?? '',
    prompt: q.prompt ?? '',
    hint: q.hint ?? '',
    category: q.category ?? 'default',
    icon: q.icon ?? '',
  }));
}

function readTheme(p: TenantBrandingPayload): ThemeInitial {
  const theme = (p.ui?.theme as Record<string, string | undefined> | undefined) ?? {};
  return {
    primary: theme.primary ?? '',
    primary_hover: theme.primary_hover ?? '',
    accent: theme.accent ?? '',
  };
}

function diffPayload(
  initial: BrandingFormState,
  current: BrandingFormState,
  questions: TenantSuggestedQuestion[] | null,
  questionsDirty: boolean
): TenantBrandingUpdateBody {
  const out: TenantBrandingUpdateBody = {};
  (Object.keys(current) as (keyof BrandingFormState)[]).forEach((k) => {
    if (current[k] !== initial[k]) out[k] = current[k];
  });
  if (questionsDirty && questions) out.suggested_questions = questions;
  return out;
}

/**
 * Admin-only branding editor. Patches `pack.yaml` (text fields +
 * suggested questions) plus reuses logo / theme endpoints for assets
 * and colors. Refreshes `/api/branding` after each save so the live UI
 * picks up the change without a restart.
 */
export function BrandingSection({ tenant }: Props) {
  const { refresh: refreshDomain } = useDomain();

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [initial, setInitial] = useState<BrandingFormState>(EMPTY_FORM);
  const [form, setForm] = useState<BrandingFormState>(EMPTY_FORM);
  const [questions, setQuestions] = useState<TenantSuggestedQuestion[]>([]);
  const [questionsInitial, setQuestionsInitial] = useState<TenantSuggestedQuestion[]>([]);
  const [themeInitial, setThemeInitial] = useState<ThemeInitial>({
    primary: '',
    primary_hover: '',
    accent: '',
  });

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    fetchTenantBranding(tenant)
      .then((p) => {
        if (cancelled) return;
        const f = readForm(p);
        setInitial(f);
        setForm(f);
        const qs = readQuestions(p);
        setQuestions(qs);
        setQuestionsInitial(qs);
        setThemeInitial(readTheme(p));
      })
      .catch((e: Error) => {
        if (!cancelled) toast.error(`Branding: ${e.message}`);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [tenant]);

  const questionsDirty = useMemo(
    () => JSON.stringify(questions) !== JSON.stringify(questionsInitial),
    [questions, questionsInitial]
  );
  const formDirty = useMemo(
    () => (Object.keys(form) as (keyof BrandingFormState)[]).some((k) => form[k] !== initial[k]),
    [form, initial]
  );

  const patch = (p: Partial<BrandingFormState>) => setForm((f) => ({ ...f, ...p }));

  const handleSave = async () => {
    const body = diffPayload(initial, form, questions, questionsDirty);
    if (Object.keys(body).length === 0) {
      toast.info('Nessuna modifica da salvare.');
      return;
    }
    setSaving(true);
    try {
      const res = await updateTenantBranding(tenant, body);
      const fresh = readForm(res);
      setInitial(fresh);
      setForm(fresh);
      const qs = readQuestions(res);
      setQuestions(qs);
      setQuestionsInitial(qs);
      refreshDomain();
      toast.success('Branding aggiornato.');
    } catch (e) {
      toast.error(`Salvataggio fallito: ${(e as Error).message}`);
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center gap-2 text-[11px] text-ink-subtle" role="status">
        <Loader2 size={12} className="animate-spin" aria-hidden /> Caricamento branding…
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <p className="text-[11px] leading-relaxed text-ink-muted">
        Modifica nome, descrizione, copy della homepage e domande suggerite. Le modifiche scrivono{' '}
        <code>pack.yaml</code> e si applicano immediatamente — nessun restart.
      </p>

      <div className="space-y-3 rounded-md border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-3">
        <SubHeader title="Identità" />
        <Field label="Nome (label)" hint="Mostrato in header e titolo della finestra.">
          <input
            type="text"
            value={form.label}
            onChange={(e) => patch({ label: e.target.value })}
            className="input-text"
            maxLength={128}
          />
        </Field>
        <Field label="Descrizione">
          <textarea
            value={form.description}
            onChange={(e) => patch({ description: e.target.value })}
            rows={2}
            className="input-text"
            maxLength={512}
          />
        </Field>
        <div className="grid grid-cols-2 gap-2">
          <Field label="App name" hint="Titolo browser, deve esistere.">
            <input
              type="text"
              value={form.app_name}
              onChange={(e) => patch({ app_name: e.target.value })}
              className="input-text"
              maxLength={128}
            />
          </Field>
          <Field label="Short name">
            <input
              type="text"
              value={form.short_name}
              onChange={(e) => patch({ short_name: e.target.value })}
              className="input-text"
              maxLength={64}
            />
          </Field>
        </div>
        <Field label="Vault label" hint="Etichetta breve per il vault.">
          <input
            type="text"
            value={form.vault_label}
            onChange={(e) => patch({ vault_label: e.target.value })}
            className="input-text"
            maxLength={64}
          />
        </Field>
      </div>

      <div className="space-y-3 rounded-md border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-3">
        <SubHeader title="Homepage" />
        <Field label="Tagline">
          <input
            type="text"
            value={form.tagline}
            onChange={(e) => patch({ tagline: e.target.value })}
            className="input-text"
            maxLength={160}
          />
        </Field>
        <div className="grid grid-cols-2 gap-2">
          <Field label="Hero question">
            <input
              type="text"
              value={form.hero_question}
              onChange={(e) => patch({ hero_question: e.target.value })}
              className="input-text"
              maxLength={160}
            />
          </Field>
          <Field label="Hero highlight">
            <input
              type="text"
              value={form.hero_highlight}
              onChange={(e) => patch({ hero_highlight: e.target.value })}
              className="input-text"
              maxLength={160}
            />
          </Field>
        </div>
        <div className="grid grid-cols-2 gap-2">
          <Field label="Hero pill">
            <input
              type="text"
              value={form.hero_pill}
              onChange={(e) => patch({ hero_pill: e.target.value })}
              className="input-text"
              maxLength={120}
            />
          </Field>
          <Field label="Hero pill icon" hint="Nome icona lucide-react.">
            <input
              type="text"
              value={form.hero_pill_icon}
              onChange={(e) => patch({ hero_pill_icon: e.target.value })}
              className="input-text"
              maxLength={64}
            />
          </Field>
        </div>
        <Field label="Empty state">
          <textarea
            value={form.empty_state}
            onChange={(e) => patch({ empty_state: e.target.value })}
            rows={2}
            className="input-text"
            maxLength={400}
          />
        </Field>
        <Field label="Disclaimer">
          <textarea
            value={form.disclaimer}
            onChange={(e) => patch({ disclaimer: e.target.value })}
            rows={2}
            className="input-text"
            maxLength={600}
          />
        </Field>
      </div>

      <BrandingQuestionsEditor questions={questions} onChange={setQuestions} />

      <div className="flex items-center justify-end gap-2 border-t border-[var(--color-border)] pt-2">
        <span className="mr-auto text-[10px] text-ink-subtle">
          {formDirty || questionsDirty ? 'Modifiche non salvate.' : 'Sincronizzato.'}
        </span>
        <Button
          variant="primary"
          onClick={handleSave}
          disabled={saving || (!formDirty && !questionsDirty)}
          className="!text-[11px]"
        >
          {saving ? <Loader2 size={11} className="animate-spin" /> : <Save size={11} />}
          Salva testi
        </Button>
      </div>

      <BrandingLogoPanel tenant={tenant} onUploaded={refreshDomain} />

      <BrandingThemePanel
        tenant={tenant}
        initial={themeInitial}
        onSaved={(next) => {
          setThemeInitial(next);
          refreshDomain();
        }}
      />

      <BrandingInputStyle />
    </div>
  );
}
