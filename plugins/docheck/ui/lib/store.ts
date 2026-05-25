import { create } from "zustand";
import type { DecisionKind, Finding, Report } from "./api";

interface AppState {
  selectedPolicies: string[];
  setSelectedPolicies: (p: string[]) => void;
  currentDocId: string | null;
  setCurrentDocId: (id: string | null) => void;
  currentReport: Report | null;
  setCurrentReport: (r: Report | null) => void;
  selectedFinding: Finding | null;
  setSelectedFinding: (f: Finding | null) => void;
  reasoningOpen: boolean;
  setReasoningOpen: (v: boolean) => void;
  openReasoningFor: (f: Finding) => void;
  detailOpen: boolean;
  setDetailOpen: (v: boolean) => void;
  openDetailFor: (f: Finding) => void;

  decisions: Record<string, DecisionKind>;
  setDecision: (findingId: string, kind: DecisionKind) => void;
  hydrateDecisions: (m: Record<string, DecisionKind>) => void;

  askFor: Finding | null;
  setAskFor: (f: Finding | null) => void;
}

export const useAppStore = create<AppState>((set) => ({
  selectedPolicies: [],
  setSelectedPolicies: (p) => set({ selectedPolicies: p }),
  currentDocId: null,
  setCurrentDocId: (id) => set({ currentDocId: id }),
  currentReport: null,
  setCurrentReport: (r) => set({ currentReport: r }),
  selectedFinding: null,
  setSelectedFinding: (f) => set({ selectedFinding: f }),
  reasoningOpen: false,
  setReasoningOpen: (v) => set({ reasoningOpen: v }),
  openReasoningFor: (f) => set({ selectedFinding: f, reasoningOpen: true }),
  detailOpen: false,
  setDetailOpen: (v) => set({ detailOpen: v }),
  openDetailFor: (f) => {
    console.log("openDetailFor invoked with", f);
    set({ selectedFinding: f, detailOpen: true });
  },

  decisions: {},
  setDecision: (findingId, kind) =>
    set((s) => ({ decisions: { ...s.decisions, [findingId]: kind } })),
  hydrateDecisions: (m) => set({ decisions: m }),

  askFor: null,
  setAskFor: (f) => set({ askFor: f }),
}));
