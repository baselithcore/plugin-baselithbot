import type { TourId } from '../../../store/app.js';
import type { TourDefinition } from '../types.js';
import { welcomeTour } from './welcome.js';
import { connectionsTour } from './connections.js';
import { nl2sqlTour } from './nl2sql.js';
import { graphTour } from './graph.js';
import { accountTour } from './account.js';

export const TOURS: Record<TourId, TourDefinition> = {
  welcome: welcomeTour,
  connections: connectionsTour,
  nl2sql: nl2sqlTour,
  graph: graphTour,
  account: accountTour,
};

export const TOUR_ORDER: TourId[] = ['welcome', 'connections', 'graph', 'nl2sql', 'account'];
