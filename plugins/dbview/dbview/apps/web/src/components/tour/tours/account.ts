import type { TourDefinition } from '../types.js';

export const accountTour: TourDefinition = {
  id: 'account',
  title: 'Account & settings',
  description: 'Profile, theme, history, users.',
  steps: [
    {
      id: 'theme',
      target: '[aria-label="Toggle theme"]',
      title: 'Theme',
      body: 'Switch between dark and light. The preference is stored locally so it survives reloads.',
      placement: 'bottom',
    },
    {
      id: 'history',
      target: '[aria-label="Query history"]',
      title: 'Query history',
      body: 'Every successful natural-language question is saved here, scoped to the current connection. Re-run, copy, or pin the ones you use most.',
      placement: 'bottom',
    },
    {
      id: 'settings',
      target: '[aria-label="Settings"]',
      title: 'Settings',
      body: 'Tune locale, default LLM provider, and graph defaults. Settings persist per-user.',
      placement: 'bottom',
    },
    {
      id: 'account',
      target: '[data-tour="user-menu"]',
      title: 'Profile menu',
      body: 'Shows your email and role. Admins also see "Manage users" — invite, promote, disable accounts. Use sign-out when you are done.',
      placement: 'bottom',
    },
  ],
};
