import { create } from 'zustand';
import type { AccessibleTab, ControlEvent, Me, PluginCard, PluginState } from '@/types';

export interface LoggedEvent extends ControlEvent {
  id: string;
  timestamp: number;
}

interface ControlStore {
  plugins: Record<string, PluginCard>;
  order: string[];
  connected: boolean;
  selected: string | null;
  me: Me | null;
  // null = central tab policy not loaded yet (fail-open until known).
  accessibleTabs: AccessibleTab[] | null;
  events: LoggedEvent[];
  latencyHistory: Record<string, number[]>;
  currentTab: 'dashboard' | 'events' | 'system';
  setTab: (tab: 'dashboard' | 'events' | 'system') => void;
  setAccessibleTabs: (tabs: AccessibleTab[]) => void;
  setInventory: (cards: PluginCard[]) => void;
  applyEvent: (event: ControlEvent) => void;
  setConnected: (connected: boolean) => void;
  select: (name: string | null) => void;
  setMe: (me: Me | null) => void;
  clearEvents: () => void;
  addLatency: (plugin: string, latency: number) => void;
  patchPlugin: (name: string, patch: Partial<PluginCard>) => void;
}

// Merge a control event delta onto a single plugin so only that card re-renders.
function mergeEvent(
  plugins: Record<string, PluginCard>,
  event: ControlEvent
): Record<string, PluginCard> {
  const name = (event.data?.plugin as string) ?? '';
  const current = plugins[name];
  if (!current) return plugins;
  const next: PluginCard = { ...current };
  if (typeof event.data?.state === 'string') {
    next.state = event.data.state as PluginState;
  }
  if (event.type === 'plugin.failed') next.healthy = false;
  if (event.type === 'plugin.activated') next.state = 'active';
  return { ...plugins, [name]: next };
}

export const useControlStore = create<ControlStore>((set) => ({
  plugins: {},
  order: [],
  connected: false,
  selected: null,
  me: null,
  accessibleTabs: null,
  events: [],
  latencyHistory: {},
  currentTab: 'dashboard',
  setTab: (tab) => set(() => ({ currentTab: tab, selected: null })), // auto-clear selected detail when switching tabs
  setAccessibleTabs: (tabs) => set(() => ({ accessibleTabs: tabs })),
  setInventory: (cards) =>
    set(() => ({
      plugins: Object.fromEntries(cards.map((c) => [c.name, c])),
      order: cards.map((c) => c.name),
    })),
  applyEvent: (event) =>
    set((s) => {
      const id = Math.random().toString(36).substring(2, 9);
      const timestamp = Date.now();
      const loggedEvent: LoggedEvent = { ...event, id, timestamp };
      const nextEvents = [loggedEvent, ...s.events].slice(0, 30);

      // Try to extract latency if present in event.data
      const name = (event.data?.plugin as string) ?? '';
      let nextLatencyHistory = s.latencyHistory;
      if (name && typeof event.data?.latency_ms === 'number') {
        const history = s.latencyHistory[name] ?? [];
        nextLatencyHistory = {
          ...s.latencyHistory,
          [name]: [...history, event.data.latency_ms].slice(-10),
        };
      }

      return {
        plugins: mergeEvent(s.plugins, event),
        events: nextEvents,
        latencyHistory: nextLatencyHistory,
      };
    }),
  setConnected: (connected) => set(() => ({ connected })),
  select: (name) => set(() => ({ selected: name })),
  setMe: (me) => set(() => ({ me })),
  clearEvents: () => set(() => ({ events: [] })),
  addLatency: (plugin, latency) =>
    set((s) => {
      const history = s.latencyHistory[plugin] ?? [];
      return {
        latencyHistory: {
          ...s.latencyHistory,
          [plugin]: [...history, latency].slice(-10),
        },
      };
    }),
  // Optimistic local patch so a toggle/action reflects instantly, without
  // waiting for the SSE round-trip (SSE still syncs other connected clients).
  patchPlugin: (name, patch) =>
    set((s) => {
      const current = s.plugins[name];
      if (!current) return s;
      return { plugins: { ...s.plugins, [name]: { ...current, ...patch } } };
    }),
}));
