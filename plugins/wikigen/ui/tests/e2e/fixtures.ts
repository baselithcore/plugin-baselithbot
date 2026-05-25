import { test as base, type Page } from '@playwright/test';

interface ApiStubs {
  /** Domain branding payload. Set `null` to simulate "no active domain → wizard". */
  branding?: object | null;
  /** Status response. */
  status?: object;
  /** Conversations list. */
  conversations?: object;
  /** Tenant list for the wizard. */
  tenants?: object;
  /** Scaffold defaults (page types, languages). */
  scaffoldDefaults?: object;
  /** Pending raw files & jobs. */
  pendingRaw?: object;
  jobs?: object;
}

const DEFAULT_BRANDING = {
  setup_mode: false,
  label: 'Knowledge Base Demo',
  description: 'Wiki dimostrativa per i test',
  ui: {
    hero_question: 'Cosa vuoi sapere',
    hero_highlight: 'dalle tue fonti?',
    hero_pill: 'Assistente · grounded sulle fonti',
    hero_pill_icon: 'Sparkles',
    empty_state:
      'Tutte le risposte sono ancorate ai documenti caricati. Ogni citazione punta al passaggio originale.',
    suggested_questions: [
      {
        category: 'copertura',
        label: 'Cosa copre la garanzia furto?',
        prompt: 'Quali eventi rientrano nella garanzia furto secondo le condizioni generali?',
        hint: 'Fonti: condizioni generali',
      },
      {
        category: 'esclusioni',
        label: 'Cosa è escluso dalla polizza?',
        prompt: 'Quali sono le principali esclusioni dalla copertura assicurativa?',
        hint: 'Fonti: clausole limitative',
      },
    ],
    disclaimer: 'I valori sono indicativi: verifica sempre la versione contrattuale corrente.',
  },
  tenant: { name: 'demo', is_active: true },
};

const DEFAULT_STATUS = {
  ok: true,
  feedback_enabled: true,
  graph_available: false,
  domain: 'demo',
};

const DEFAULT_CONVERSATIONS = { conversations: [] };

const DEFAULT_TENANTS = {
  active: 'demo',
  tenants: [
    {
      name: 'demo',
      label: 'Knowledge Base Demo',
      description: 'Wiki dimostrativa',
      language: 'it',
      page_types: ['source', 'entity', 'concept'],
      is_active: true,
      is_seed: false,
      valid: true,
    },
    {
      name: 'legal',
      label: 'Wiki Legale',
      description: 'Sentenze e normativa',
      language: 'it',
      page_types: ['source', 'entity', 'concept', 'topic'],
      is_active: false,
      is_seed: true,
      valid: true,
    },
  ],
};

const DEFAULT_SCAFFOLD_DEFAULTS = {
  languages: ['it', 'en'],
  suggested_page_types: [
    { id: 'source' },
    { id: 'entity' },
    { id: 'concept' },
    { id: 'topic' },
  ],
};

export async function installApiStubs(page: Page, stubs: ApiStubs = {}) {
  const branding = stubs.branding ?? DEFAULT_BRANDING;
  const status = stubs.status ?? DEFAULT_STATUS;
  const conversations = stubs.conversations ?? DEFAULT_CONVERSATIONS;
  const tenants = stubs.tenants ?? DEFAULT_TENANTS;
  const scaffoldDefaults = stubs.scaffoldDefaults ?? DEFAULT_SCAFFOLD_DEFAULTS;
  const pendingRaw = stubs.pendingRaw ?? { count: 0, files: [] };
  const jobs = stubs.jobs ?? { count: 0, jobs: [] };

  await page.route('**/api/branding*', (route) =>
    route.fulfill({ json: branding ?? { setup_mode: true } }),
  );
  await page.route('**/api/status*', (route) => route.fulfill({ json: status }));
  await page.route('**/api/conversations*', (route) => route.fulfill({ json: conversations }));
  await page.route('**/api/groups*', (route) => route.fulfill({ json: { groups: [] } }));
  await page.route('**/api/admin/scaffold/defaults*', (route) =>
    route.fulfill({ json: scaffoldDefaults }),
  );
  await page.route('**/api/admin/tenants*', (route) => route.fulfill({ json: tenants }));
  await page.route('**/api/ingest/raw/pending*', (route) => route.fulfill({ json: pendingRaw }));
  await page.route('**/api/ingest/raw/jobs*', (route) => route.fulfill({ json: jobs }));
  await page.route('**/api/raw/files*', (route) =>
    route.fulfill({ json: { count: 0, files: [] } }),
  );
  // Catch-all: stub anything else with 200 empty so the app doesn't fall over.
  await page.route('**/api/**', (route) => route.fulfill({ json: {} }));
}

export const test = base.extend<{ stubbedPage: Page }>({
  stubbedPage: async ({ page }, use) => {
    await installApiStubs(page);
    await use(page);
  },
});

export { expect } from '@playwright/test';
