import type { TourId } from '../../store/app.js';

export type StepPlacement = 'top' | 'bottom' | 'left' | 'right' | 'center';

export interface TourStep {
  id: string;
  target?: string;
  title: string;
  body: string;
  placement?: StepPlacement;
  padding?: number;
  onEnter?: () => void;
  onLeave?: () => void;
  allowSkipToEnd?: boolean;
}

export interface TourDefinition {
  id: TourId;
  title: string;
  description: string;
  steps: TourStep[];
}
