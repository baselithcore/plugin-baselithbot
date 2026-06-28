import { create } from 'zustand';
import type {
  AccessibleTab,
  ControlEvent,
  CostUsageView,
  Me,
  PluginCard,
  PluginCostRow,
  PluginState,
} from '@/types';

export interface LoggedEvent extends ControlEvent {
  id: string;
  timestamp: number;
}

// Per-plugin LLM spend aggregate (summed across the plugin's models).
export interface PluginCostAgg {
  cost_usd: number;
  total_tokens: number;
  calls: number;
  rows: PluginCostRow[];
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
  costByPlugin: Record<string, PluginCostAgg>;
  currentTab: 'dashboard' | 'events' | 'logs' | 'system';
  setTab: (tab: 'dashboard' | 'events' | 'logs' | 'system') => void;
  setAccessibleTabs: (tabs: AccessibleTab[]) => void;
  setCostUsage: (view: CostUsageView) => void;
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
  costByPlugin: {},
  currentTab: 'dashboard',
  setTab: (tab) => set(() => ({ currentTab: tab, selected: null })), // auto-clear selected detail when switching tabs
  setAccessibleTabs: (tabs) => set(() => ({ accessibleTabs: tabs })),
  // Group the flat per-(plugin,model) usage rows into a per-plugin aggregate so
  // cards and the detail view can read their slice cheaply.
  setCostUsage: (view) =>
    set(() => {
      const map: Record<string, PluginCostAgg> = {};
      for (const r of view.rows) {
        const agg =
          map[r.plugin] ?? (map[r.plugin] = { cost_usd: 0, total_tokens: 0, calls: 0, rows: [] });
        agg.cost_usd += r.cost_usd;
        agg.total_tokens += r.total_tokens;
        agg.calls += r.calls;
        agg.rows.push(r);
      }
      return { costByPlugin: map };
    }),
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
