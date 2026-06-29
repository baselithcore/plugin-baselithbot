import { create } from 'zustand';

import type { TabId } from '../types';

interface UIState {
  tab: TabId;
  setTab: (tab: TabId) => void;
}

export const useUI = create<UIState>((set) => ({
  tab: 'incidents',
  setTab: (tab) => set({ tab }),
}));
