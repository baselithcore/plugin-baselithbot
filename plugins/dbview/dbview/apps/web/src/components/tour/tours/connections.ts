import type { TourDefinition } from '../types.js';

export const connectionsTour: TourDefinition = {
  id: 'connections',
  title: 'Connections tour',
  description: 'Create, switch, share databases.',
  steps: [
    {
      id: 'panel',
      target: '[data-tour="connections-panel"]',
      title: 'Connections pane',
      body: 'All your databases are grouped by family — relational, graph, document, vector, search, SaaS. The active one is highlighted with an accent bar.',
      placement: 'right',
    },
    {
      id: 'new',
      target: '[data-tour="connections-panel"] [aria-label="New connection"]',
      title: 'Add a connection (admins)',
      body: 'Admins can paste a connection string or fill in host/port/database. The form tests reachability before saving and encrypts the secret at rest.',
      placement: 'right',
    },
    {
      id: 'search',
      target: '[data-tour="connections-panel"] [role="searchbox"]',
      title: 'Find a connection',
      body: 'Filter by name, host, database, or dialect. Press ⌘F to focus, Enter to activate the first match, Esc to clear.',
      placement: 'right',
    },
    {
      id: 'sharing',
      target: '[data-tour="connections-panel"]',
      title: 'Share with the team',
      body: 'Hover an entry as an admin to share it: with all users, all admins, a specific list, or keep it private. Sharing mode is shown by the badge next to the name.',
      placement: 'right',
    },
  ],
};
