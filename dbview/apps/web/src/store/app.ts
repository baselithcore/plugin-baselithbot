import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { LlmProvider, Nl2SqlResponse, ResponseLocale } from '@dbview/shared';
import type { ChatTurn } from '../components/nl2query/turn-types.js';

type Theme = 'dark' | 'light';

interface DetailSelection {
  tableId: string;
  columnName?: string;
}

export type TourId = 'welcome' | 'connections' | 'nl2sql' | 'graph' | 'account';
export type ChecklistTaskId =
  'connect' | 'explore-schema' | 'ask-question' | 'open-detail' | 'use-command-palette';

interface AppState {
  activeConnectionId: string | null;
  provider: LlmProvider;
  model: string | undefined;
  responseLocale: ResponseLocale;
  lastResponse: Nl2SqlResponse | null;
  highlightedTables: Set<string>;
  hoveredEntities: Set<string>;
  conversation: ChatTurn[];
  autoExecute: boolean;
  theme: Theme;
  commandOpen: boolean;
  settingsOpen: boolean;
  usersOpen: boolean;
  historyOpen: boolean;
  schemaSearch: string;
  detailSelection: DetailSelection | null;
  graphView3D: boolean;
  graphDataMode: 'schema' | 'data';
  resultView3D: boolean;
  leftCollapsed: boolean;
  rightCollapsed: boolean;
  minimapVisible: boolean;
  legendVisible: boolean;
  activeTour: TourId | null;
  tourStepIndex: number;
  toursCompleted: TourId[];
  toursSeen: TourId[];
  checklistDone: ChecklistTaskId[];
  checklistDismissed: boolean;
  startTour: (id: TourId) => void;
  nextTourStep: () => void;
  prevTourStep: () => void;
  stopTour: (completed?: boolean) => void;
  markChecklistDone: (id: ChecklistTaskId) => void;
  dismissChecklist: () => void;
  resetOnboarding: () => void;
  setActiveConnection: (id: string | null) => void;
  setProvider: (p: LlmProvider) => void;
  setModel: (m: string | undefined) => void;
  setResponseLocale: (l: ResponseLocale) => void;
  setLastResponse: (r: Nl2SqlResponse | null) => void;
  addTurn: (t: ChatTurn) => void;
  updateTurn: (id: string, patch: Partial<ChatTurn>) => void;
  clearConversation: () => void;
  setAutoExecute: (v: boolean) => void;
  setTheme: (t: Theme) => void;
  toggleTheme: () => void;
  setCommandOpen: (v: boolean) => void;
  setSettingsOpen: (v: boolean) => void;
  setUsersOpen: (v: boolean) => void;
  setHistoryOpen: (v: boolean) => void;
  setSchemaSearch: (q: string) => void;
  setHoveredEntities: (ids: Iterable<string> | null) => void;
  selectTable: (tableId: string) => void;
  selectColumn: (tableId: string, columnName: string) => void;
  closeDetail: () => void;
  setGraphView3D: (v: boolean) => void;
  setGraphDataMode: (m: 'schema' | 'data') => void;
  setResultView3D: (v: boolean) => void;
  setLeftCollapsed: (v: boolean) => void;
  setRightCollapsed: (v: boolean) => void;
  toggleLeftCollapsed: () => void;
  toggleRightCollapsed: () => void;
  setMinimapVisible: (v: boolean) => void;
  toggleMinimapVisible: () => void;
  setLegendVisible: (v: boolean) => void;
  toggleLegendVisible: () => void;
}

export const useAppStore = create<AppState>()(
  persist(
    (set, get) => ({
      activeConnectionId: null,
      provider: 'ollama',
      model: undefined,
      responseLocale: detectInitialLocale(),
      lastResponse: null,
      highlightedTables: new Set(),
      hoveredEntities: new Set(),
      conversation: [],
      autoExecute: true,
      theme: 'dark',
      commandOpen: false,
      settingsOpen: false,
      usersOpen: false,
      historyOpen: false,
      schemaSearch: '',
      detailSelection: null,
      graphView3D: false,
      graphDataMode: 'schema',
      resultView3D: false,
      leftCollapsed: false,
      rightCollapsed: false,
      minimapVisible: true,
      legendVisible: true,
      activeTour: null,
      tourStepIndex: 0,
      toursCompleted: [],
      toursSeen: [],
      checklistDone: [],
      checklistDismissed: false,
      startTour: (id) => {
        const seen = get().toursSeen;
        set({
          activeTour: id,
          tourStepIndex: 0,
          toursSeen: seen.includes(id) ? seen : [...seen, id],
        });
      },
      nextTourStep: () => set({ tourStepIndex: get().tourStepIndex + 1 }),
      prevTourStep: () => set({ tourStepIndex: Math.max(0, get().tourStepIndex - 1) }),
      stopTour: (completed) => {
        const id = get().activeTour;
        if (completed && id && !get().toursCompleted.includes(id)) {
          set({ toursCompleted: [...get().toursCompleted, id] });
        }
        set({ activeTour: null, tourStepIndex: 0 });
      },
      markChecklistDone: (id) => {
        if (get().checklistDone.includes(id)) return;
        set({ checklistDone: [...get().checklistDone, id] });
      },
      dismissChecklist: () => set({ checklistDismissed: true }),
      resetOnboarding: () =>
        set({
          activeTour: null,
          tourStepIndex: 0,
          toursCompleted: [],
          toursSeen: [],
          checklistDone: [],
          checklistDismissed: false,
        }),
      setActiveConnection: (id) =>
        set({
          activeConnectionId: id,
          lastResponse: null,
          highlightedTables: new Set(),
          hoveredEntities: new Set(),
          conversation: [],
          detailSelection: null,
        }),
      setProvider: (provider) => set({ provider }),
      setModel: (model) => set({ model }),
      setResponseLocale: (responseLocale) => set({ responseLocale }),
      setLastResponse: (lastResponse) =>
        set({
          lastResponse,
          highlightedTables: new Set(lastResponse?.involvedEntities ?? []),
        }),
      addTurn: (turn) => set({ conversation: [...get().conversation, turn] }),
      updateTurn: (id, patch) =>
        set({
          conversation: get().conversation.map((t) => (t.id === id ? { ...t, ...patch } : t)),
        }),
      clearConversation: () => set({ conversation: [] }),
      setAutoExecute: (autoExecute) => set({ autoExecute }),
      setTheme: (theme) => {
        document.documentElement.classList.toggle('light', theme === 'light');
        document.documentElement.classList.toggle('dark', theme === 'dark');
        set({ theme });
      },
      toggleTheme: () => {
        const next: Theme = get().theme === 'dark' ? 'light' : 'dark';
        get().setTheme(next);
      },
      setCommandOpen: (commandOpen) => set({ commandOpen }),
      setSettingsOpen: (settingsOpen) => set({ settingsOpen }),
      setUsersOpen: (usersOpen) => set({ usersOpen }),
      setHistoryOpen: (historyOpen) => set({ historyOpen }),
      setSchemaSearch: (schemaSearch) => set({ schemaSearch }),
      setHoveredEntities: (ids) => set({ hoveredEntities: new Set(ids ?? []) }),
      selectTable: (tableId) => set({ detailSelection: { tableId } }),
      selectColumn: (tableId, columnName) => set({ detailSelection: { tableId, columnName } }),
      closeDetail: () => set({ detailSelection: null }),
      setGraphView3D: (graphView3D) => set({ graphView3D }),
      setGraphDataMode: (graphDataMode) => set({ graphDataMode }),
      setResultView3D: (resultView3D) => set({ resultView3D }),
      setLeftCollapsed: (leftCollapsed) => set({ leftCollapsed }),
      setRightCollapsed: (rightCollapsed) => set({ rightCollapsed }),
      toggleLeftCollapsed: () => set({ leftCollapsed: !get().leftCollapsed }),
      toggleRightCollapsed: () => set({ rightCollapsed: !get().rightCollapsed }),
      setMinimapVisible: (minimapVisible) => set({ minimapVisible }),
      toggleMinimapVisible: () => set({ minimapVisible: !get().minimapVisible }),
      setLegendVisible: (legendVisible) => set({ legendVisible }),
      toggleLegendVisible: () => set({ legendVisible: !get().legendVisible }),
    }),
    {
      name: 'dbview-ui',
      partialize: (s) => ({
        activeConnectionId: s.activeConnectionId,
        provider: s.provider,
        model: s.model,
        responseLocale: s.responseLocale,
        theme: s.theme,
        autoExecute: s.autoExecute,
        graphView3D: s.graphView3D,
        graphDataMode: s.graphDataMode,
        resultView3D: s.resultView3D,
        leftCollapsed: s.leftCollapsed,
        rightCollapsed: s.rightCollapsed,
        minimapVisible: s.minimapVisible,
        legendVisible: s.legendVisible,
        toursCompleted: s.toursCompleted,
        toursSeen: s.toursSeen,
        checklistDone: s.checklistDone,
        checklistDismissed: s.checklistDismissed,
      }),
    }
  )
);

function detectInitialLocale(): ResponseLocale {
  if (typeof navigator === 'undefined') return 'en';
  const lang = navigator.language?.toLowerCase() ?? '';
  return lang.startsWith('it') ? 'it' : 'en';
}
