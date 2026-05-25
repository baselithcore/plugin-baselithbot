import type { TourDefinition } from '../types.js';

export const graphTour: TourDefinition = {
  id: 'graph',
  title: 'Schema graph tour',
  description: 'Navigate, search, inspect.',
  steps: [
    {
      id: 'viewport',
      target: '[data-tour="graph-viewport"]',
      title: 'Schema canvas',
      body: 'Tables are laid out with dagre. Edges represent foreign keys. Tables highlighted in the most recent query glow with an accent ring.',
      placement: 'left',
    },
    {
      id: 'toolbar',
      target: '[data-tour="graph-toolbar"]',
      title: 'Toolbar',
      body: 'Search the schema, toggle 2D/3D, swap between schema and data preview, show/hide the minimap and legend.',
      placement: 'bottom',
    },
    {
      id: 'detail',
      target: '[data-tour="graph-viewport"]',
      title: 'Inspect tables and columns',
      body: 'Click any table to open the detail drawer with columns, types, indexes, and sample rows. Click a column name inside the drawer to focus on it.',
      placement: 'left',
    },
  ],
};
