import type { PluginTab } from '../../../types';

/** Mutable form state collected across the wizard steps. */
export interface WizardData {
  email: string;
  username: string;
  autoGenerate: boolean;
  password: string;
  roles: string[];
  allowedTabs: string[];
}

export interface StepProps {
  data: WizardData;
  update: <K extends keyof WizardData>(key: K, value: WizardData[K]) => void;
  availableTabs: PluginTab[];
}

export const INITIAL_DATA: WizardData = {
  email: '',
  username: '',
  autoGenerate: true,
  password: '',
  roles: ['user'],
  allowedTabs: [],
};
