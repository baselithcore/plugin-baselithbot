import type { TourDefinition } from '../types.js';

export const welcomeTour: TourDefinition = {
  id: 'welcome',
  title: 'Welcome to dbview',
  description: 'Quick tour of the workspace — about 60 seconds.',
  steps: [
    {
      id: 'intro',
      title: 'Welcome to dbview',
      body: 'A unified workspace to explore databases and ask questions in natural language. We will walk through the three panes and the most useful shortcuts.',
      placement: 'center',
    },
    {
      id: 'connections',
      target: '[data-tour="connections-panel"]',
      title: 'Connections',
      body: 'Manage your databases here. Admins can add and share them; everyone can switch between them. Click a connection to load its schema.',
      placement: 'right',
    },
    {
      id: 'graph',
      target: '[data-tour="graph-viewport"]',
      title: 'Schema graph',
      body: 'Tables become nodes, foreign keys become edges. Drag to pan, scroll to zoom, click a table to inspect it. Toggle 2D/3D from the toolbar.',
      placement: 'left',
    },
    {
      id: 'nl2query',
      target: '[data-tour="nl2query-panel"]',
      title: 'Query assistant',
      body: 'Ask in plain English or Italian. dbview drafts a safe SQL query, runs it, and explains the result. Try a suggested question to start.',
      placement: 'left',
    },
    {
      id: 'palette',
      target: '[data-tour="command-palette-button"]',
      title: 'Command palette',
      body: 'Press ⌘K (Ctrl+K) anywhere to jump between connections, open settings, or trigger any action without leaving the keyboard.',
      placement: 'bottom',
    },
    {
      id: 'help',
      target: '[data-tour="help-button"]',
      title: 'Tours and help',
      body: 'Re-open this tour anytime from the help menu, or pick a focused tour for one specific area.',
      placement: 'bottom',
    },
    {
      id: 'account',
      target: '[data-tour="user-menu"]',
      title: 'Account',
      body: 'Your profile lives here. Open it to see your role, sign out, or — if you are an admin — invite teammates and manage users.',
      placement: 'bottom',
    },
  ],
};
