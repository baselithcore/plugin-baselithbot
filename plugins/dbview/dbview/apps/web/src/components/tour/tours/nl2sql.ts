import type { TourDefinition } from '../types.js';

export const nl2sqlTour: TourDefinition = {
  id: 'nl2sql',
  title: 'Query assistant tour',
  description: 'Natural language to SQL, safely.',
  steps: [
    {
      id: 'panel',
      target: '[data-tour="nl2query-panel"]',
      title: 'Query assistant',
      body: 'Ask plain-language questions and get back a safe, executable SQL query plus a one-paragraph answer. Conversation history is kept so follow-up questions resolve pronouns and prior filters.',
      placement: 'left',
    },
    {
      id: 'composer',
      target: '[data-tour="nl2query-composer"]',
      title: 'Compose a prompt',
      body: 'Type your question and press Enter (Shift+Enter for newline). The assistant uses your current connection schema as grounding.',
      placement: 'top',
    },
    {
      id: 'provider',
      target: '[data-tour="nl2query-provider"]',
      title: 'Provider & model',
      body: 'Choose Ollama (local), OpenAI, or Anthropic. Models that cannot follow JSON instructions are hidden automatically.',
      placement: 'top',
    },
    {
      id: 'auto',
      target: '[data-tour="nl2query-auto"]',
      title: 'Auto-execute',
      body: 'When on, the generated query runs immediately and you get an answer. Turn it off to inspect the SQL first and run it manually.',
      placement: 'top',
    },
    {
      id: 'safety',
      target: '[data-tour="nl2query-panel"]',
      title: 'Built-in safety',
      body: 'Every query is parsed and validated: no SELECT *, no DDL, single statement only, auto-injected LIMIT, read-only transaction at the DB level. DML is blocked unless explicitly allowed.',
      placement: 'left',
    },
  ],
};
