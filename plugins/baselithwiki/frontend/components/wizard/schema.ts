import { z } from 'zod';
import type { ScaffoldRequestBody } from '../../lib/api';

const SLUG_RE = /^[a-z][a-z0-9_-]*$/;

export const wizardSchema = z.object({
  name: z
    .string()
    .min(1, 'obbligatorio')
    .max(64)
    .regex(SLUG_RE, "snake-case ASCII (es. 'legal', 'my_wiki', 'team-2')")
    .refine((v) => v !== '_template' && v !== 'default' && v !== 'active', 'nome riservato'),
  label: z.string().max(128).optional().default(''),
  description: z.string().max(512).optional().default(''),
  language: z.string().regex(/^[a-z]{2}(-[A-Z]{2})?$/, "es. 'it', 'en', 'en-US'"),
  vault_root: z
    .string()
    .optional()
    .default('')
    .refine(
      (v) => !v || v.startsWith('/') || v.startsWith('~/'),
      'percorso assoluto richiesto (deve iniziare con / o ~/)'
    ),
  activate: z.boolean(),
  synthesize_prompts: z.boolean(),
  from_seed: z.string().optional().default(''),
  // branding step
  theme_primary: z
    .string()
    .optional()
    .default('')
    .refine((v) => !v || /^#[0-9A-Fa-f]{6}$/.test(v), 'hex 6 cifre richiesto'),
  theme_primary_hover: z
    .string()
    .optional()
    .default('')
    .refine((v) => !v || /^#[0-9A-Fa-f]{6}$/.test(v), 'hex 6 cifre richiesto'),
  theme_accent: z
    .string()
    .optional()
    .default('')
    .refine((v) => !v || /^#[0-9A-Fa-f]{6}$/.test(v), 'hex 6 cifre richiesto'),
  use_provider: z.boolean(),
  provider_vendor: z.enum(['ollama', 'openai']).optional(),
  provider_rag_vendor: z.enum(['ollama', 'openai']).optional(),
  provider_ingest_vendor: z.enum(['ollama', 'openai']).optional(),
  provider_model: z.string().optional().default(''),
  provider_ingest_model: z.string().optional().default(''),
  provider_base_url: z.string().optional().default(''),
  provider_api_key: z.string().optional().default(''),
  provider_ollama_url: z.string().optional().default(''),
  provider_openai_api_base: z.string().optional().default(''),
  provider_openai_api_key: z.string().optional().default(''),
});

export type WizardForm = z.infer<typeof wizardSchema>;

export const DEFAULT_FORM: WizardForm = {
  name: '',
  label: '',
  description: '',
  language: 'it',
  vault_root: '',
  activate: true,
  synthesize_prompts: true,
  from_seed: '',
  theme_primary: '',
  theme_primary_hover: '',
  theme_accent: '',
  use_provider: false,
  provider_vendor: 'ollama',
  provider_rag_vendor: 'ollama',
  provider_ingest_vendor: 'ollama',
  provider_model: '',
  provider_ingest_model: '',
  provider_base_url: '',
  provider_api_key: '',
  provider_ollama_url: '',
  provider_openai_api_base: '',
  provider_openai_api_key: '',
};

export type Step = 'identity' | 'vault' | 'branding' | 'documents' | 'provider' | 'review' | 'done';

export const STEPS: { id: Step; label: string }[] = [
  { id: 'identity', label: 'Identità' },
  { id: 'vault', label: 'Vault' },
  { id: 'branding', label: 'Branding' },
  { id: 'documents', label: 'Documenti' },
  { id: 'provider', label: 'Provider' },
  { id: 'review', label: 'Revisione' },
];

export const DRAFT_KEY = 'llm-wiki:wizard-draft';

export function buildScaffoldBody(v: WizardForm): ScaffoldRequestBody {
  const body: ScaffoldRequestBody = {
    name: v.name,
    label: v.label?.trim() || undefined,
    description: v.description?.trim() || undefined,
    language: v.language,
    vault_root: v.vault_root?.trim() || undefined,
    write_env: true,
    activate: v.activate,
    force: false,
    from_seed: v.from_seed?.trim() || null,
    synthesize_prompts: v.synthesize_prompts,
  };
  if (v.use_provider) {
    const ragVendor = v.provider_rag_vendor ?? v.provider_vendor ?? 'ollama';
    const ingestVendor = v.provider_ingest_vendor ?? v.provider_vendor ?? 'ollama';
    body.provider = {
      // LLM_VENDOR fallback baseline — pick chat vendor as canonical so
      // single-vendor consumers reading LLM_VENDOR see a sensible value.
      vendor: ragVendor,
      rag_vendor: ragVendor,
      ingest_vendor: ingestVendor,
      model: v.provider_model?.trim() || undefined,
      ingest_model: v.provider_ingest_model?.trim() || undefined,
      ollama_url: v.provider_ollama_url?.trim() || undefined,
      openai_api_base: v.provider_openai_api_base?.trim() || undefined,
      openai_api_key: v.provider_openai_api_key?.trim() || undefined,
    };
  }
  return body;
}
