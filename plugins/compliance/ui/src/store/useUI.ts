import { create } from 'zustand';

import type { TabId } from '../types';

interface UIState {
  tab: TabId;
  sidebarOpen: boolean;
  setTab: (tab: TabId) => void;
  toggleSidebar: () => void;
}

export const useUI = create<UIState>((set) => ({
  tab: 'overview',
  sidebarOpen: false,
  setTab: (tab) => set({ tab, sidebarOpen: false }),
  toggleSidebar: () => set((s) => ({ sidebarOpen: !s.sidebarOpen })),
}));
