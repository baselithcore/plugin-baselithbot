// Global UI + data store (zustand). Keeps the indexing/data concerns (notes,
// graph) cleanly separated from React component rendering.
import { create } from 'zustand';
import { api } from './lib/api';
import type { ConversationMeta, Note, NoteMeta, TreeNode, WorkspaceInfo } from './lib/types';

type Theme = 'light' | 'dark';

const WS_KEY = 'bb-workspace';
const PIN_KEY = 'bb-pinned';
const RECENT_KEY = 'bb-recent';
const RECENT_MAX = 8;

function loadIds(key: string): string[] {
  try {
    const raw = JSON.parse(localStorage.getItem(key) || '[]');
    return Array.isArray(raw) ? raw.filter((x): x is string => typeof x === 'string') : [];
  } catch {
    return [];
  }
}

function saveIds(key: string, ids: string[]): void {
  localStorage.setItem(key, JSON.stringify(ids));
}

function initialTheme(): Theme {
  const saved = localStorage.getItem('bb-theme');
  if (saved === 'light' || saved === 'dark') return saved;
  return document.documentElement.classList.contains('dark') ? 'dark' : 'light';
}

function applyTheme(theme: Theme): void {
  document.documentElement.classList.toggle('dark', theme === 'dark');
  localStorage.setItem('bb-theme', theme);
}

function initialWorkspace(): string {
  return localStorage.getItem(WS_KEY) || 'default';
}

interface BrainState {
  notes: NoteMeta[];
  tree: TreeNode[];
  activeId: string | null;
  active: Note | null;
  loading: boolean;
  theme: Theme;
  paletteOpen: boolean;
  graphOpen: boolean;
  assistantOpen: boolean;
  workspaces: WorkspaceInfo[];
  activeWorkspace: string;
  conversations: ConversationMeta[];
  activeConversationId: string | null;
  pinned: string[];
  recent: string[];
  focusMode: boolean;
  //: Which secondary modal/drawer is open (mounted once at the app root).
  modal: 'history' | 'templates' | 'trash' | null;
  //: Bumped only when the active note's body is replaced *externally* (e.g. a
  //: history restore), so the editor remounts and reloads — never on a normal
  //: debounced save, which would otherwise reset the caret on every keystroke.
  reloadToken: number;

  init: () => Promise<void>;
  loadNotes: () => Promise<void>;
  loadTree: () => Promise<void>;
  openNote: (id: string) => Promise<void>;
  openByTitle: (title: string) => Promise<void>;
  openWiki: (target: string, label?: string) => Promise<void>;
  createNote: (title?: string, parent?: string | null) => Promise<void>;
  moveNote: (id: string, parent: string | null, order?: number) => Promise<void>;
  deleteNote: (id: string) => Promise<void>;
  applyServerNote: (note: Note) => void;

  loadWorkspaces: () => Promise<void>;
  switchWorkspace: (id: string) => Promise<void>;
  createWorkspace: (name: string, color?: string | null) => Promise<void>;
  deleteWorkspace: (id: string) => Promise<void>;
  assignNoteWorkspace: (id: string, workspace: string) => Promise<void>;

  loadConversations: () => Promise<void>;
  setActiveConversation: (id: string | null) => void;
  deleteConversation: (id: string) => Promise<void>;
  renameConversation: (id: string, title: string) => Promise<void>;

  openDaily: () => Promise<void>;
  refreshActive: (id: string) => Promise<void>;
  togglePin: (id: string) => void;
  pushRecent: (id: string) => void;

  setModal: (modal: 'history' | 'templates' | 'trash' | null) => void;
  toggleTheme: () => void;
  toggleFocus: () => void;
  setPalette: (open: boolean) => void;
  toggleGraph: () => void;
  setAssistant: (open: boolean) => void;
  toggleAssistant: () => void;
}

export const useBrain = create<BrainState>((set, get) => ({
  notes: [],
  tree: [],
  activeId: null,
  active: null,
  loading: false,
  theme: initialTheme(),
  paletteOpen: false,
  graphOpen: false,
  assistantOpen: false,
  workspaces: [],
  activeWorkspace: initialWorkspace(),
  conversations: [],
  activeConversationId: null,
  pinned: loadIds(PIN_KEY),
  recent: loadIds(RECENT_KEY),
  focusMode: false,
  modal: null,
  reloadToken: 0,

  init: async () => {
    applyTheme(get().theme);
    await get().loadWorkspaces();
    await Promise.all([get().loadNotes(), get().loadTree(), get().loadConversations()]);
    const first = get().notes[0];
    if (first) await get().openNote(first.id);
  },

  loadNotes: async () => {
    const notes = await api.listNotes(get().activeWorkspace);
    notes.sort((a, b) => (b.updated || '').localeCompare(a.updated || ''));
    set({ notes });
  },

  loadTree: async () => {
    set({ tree: await api.tree(get().activeWorkspace) });
  },

  openNote: async (id) => {
    set({ loading: true, activeId: id });
    try {
      const note = await api.getNote(id);
      set({ active: note });
      get().pushRecent(id);
    } finally {
      set({ loading: false });
    }
  },

  openByTitle: async (title) => {
    const slug = title
      .toLowerCase()
      .normalize('NFKD')
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/^-+|-+$/g, '');
    const existing = get().notes.find((n) => n.id === slug);
    if (existing) {
      await get().openNote(existing.id);
      return;
    }
    const note = await api.createNote({ title, workspace: get().activeWorkspace });
    await Promise.all([get().loadNotes(), get().loadTree()]);
    set({ active: note, activeId: note.id });
  },

  openWiki: async (target, label) => {
    const existing = get().notes.find((n) => n.id === target);
    if (existing) {
      await get().openNote(existing.id);
      return;
    }
    const note = await api.createNote({
      title: label || target,
      workspace: get().activeWorkspace,
    });
    await Promise.all([get().loadNotes(), get().loadTree()]);
    set({ active: note, activeId: note.id });
  },

  createNote: async (title = 'Untitled', parent = null) => {
    const note = await api.createNote({
      title,
      body: '',
      parent,
      workspace: get().activeWorkspace,
    });
    await Promise.all([get().loadNotes(), get().loadTree(), get().loadWorkspaces()]);
    set({ active: note, activeId: note.id });
  },

  moveNote: async (id, parent, order) => {
    await api.moveNote(id, { parent, ...(order !== undefined ? { order } : {}) });
    await Promise.all([get().loadNotes(), get().loadTree()]);
  },

  deleteNote: async (id) => {
    await api.deleteNote(id);
    const pinned = get().pinned.filter((x) => x !== id);
    const recent = get().recent.filter((x) => x !== id);
    saveIds(PIN_KEY, pinned);
    saveIds(RECENT_KEY, recent);
    set({ pinned, recent });
    await Promise.all([get().loadNotes(), get().loadTree(), get().loadWorkspaces()]);
    if (get().activeId === id) {
      const next = get().notes[0];
      if (next) await get().openNote(next.id);
      else set({ active: null, activeId: null });
    }
  },

  applyServerNote: (note) => {
    set((s) => ({
      active: s.activeId === note.id ? note : s.active,
      notes: s.notes.map((n) =>
        n.id === note.id ? { ...n, title: note.title, tags: note.tags, updated: note.updated } : n
      ),
    }));
  },

  loadWorkspaces: async () => {
    const workspaces = await api.listWorkspaces();
    // Heal a dangling selection (deleted workspace) → fall back to default.
    const active = get().activeWorkspace;
    const exists = workspaces.some((w) => w.id === active);
    set({ workspaces, activeWorkspace: exists ? active : 'default' });
  },

  switchWorkspace: async (id) => {
    if (id === get().activeWorkspace) return;
    localStorage.setItem(WS_KEY, id);
    // Chat threads are workspace-scoped — drop the active thread on switch.
    set({ activeWorkspace: id, active: null, activeId: null, activeConversationId: null });
    await Promise.all([get().loadNotes(), get().loadTree(), get().loadConversations()]);
    const first = get().notes[0];
    if (first) await get().openNote(first.id);
  },

  createWorkspace: async (name, color = null) => {
    const ws = await api.createWorkspace({ name, color });
    await get().loadWorkspaces();
    await get().switchWorkspace(ws.id);
  },

  deleteWorkspace: async (id) => {
    await api.deleteWorkspace(id);
    if (get().activeWorkspace === id) {
      localStorage.setItem(WS_KEY, 'default');
      set({ activeWorkspace: 'default' });
    }
    await get().loadWorkspaces();
    await Promise.all([get().loadNotes(), get().loadTree()]);
  },

  assignNoteWorkspace: async (id, workspace) => {
    await api.assignNoteWorkspace(id, workspace);
    await Promise.all([get().loadNotes(), get().loadTree(), get().loadWorkspaces()]);
    // The note left the current view if moved out of the active workspace.
    if (workspace !== get().activeWorkspace && get().activeId === id) {
      const next = get().notes[0];
      if (next) await get().openNote(next.id);
      else set({ active: null, activeId: null });
    }
  },

  loadConversations: async () => {
    const conversations = await api.listConversations(get().activeWorkspace);
    // Heal a dangling active thread (deleted elsewhere) → none selected.
    const active = get().activeConversationId;
    const exists = conversations.some((c) => c.id === active);
    set({ conversations, activeConversationId: exists ? active : null });
  },

  setActiveConversation: (id) => set({ activeConversationId: id }),

  deleteConversation: async (id) => {
    await api.deleteConversation(id);
    set((s) => ({
      conversations: s.conversations.filter((c) => c.id !== id),
      activeConversationId: s.activeConversationId === id ? null : s.activeConversationId,
    }));
  },

  renameConversation: async (id, title) => {
    const conv = await api.renameConversation(id, title);
    set((s) => ({
      conversations: s.conversations.map((c) =>
        c.id === id ? { ...c, title: conv.title, updated: conv.updated } : c
      ),
    }));
  },

  openDaily: async () => {
    const note = await api.openDaily();
    await Promise.all([get().loadNotes(), get().loadTree(), get().loadWorkspaces()]);
    set({ active: note, activeId: note.id });
    get().pushRecent(note.id);
  },

  refreshActive: async (id) => {
    const note = await api.getNote(id);
    await get().loadNotes();
    set((s) => ({ active: note, activeId: id, reloadToken: s.reloadToken + 1 }));
  },

  togglePin: (id) => {
    set((s) => {
      const pinned = s.pinned.includes(id) ? s.pinned.filter((x) => x !== id) : [...s.pinned, id];
      saveIds(PIN_KEY, pinned);
      return { pinned };
    });
  },

  pushRecent: (id) => {
    set((s) => {
      const recent = [id, ...s.recent.filter((x) => x !== id)].slice(0, RECENT_MAX);
      saveIds(RECENT_KEY, recent);
      return { recent };
    });
  },

  toggleTheme: () => {
    const theme = get().theme === 'dark' ? 'light' : 'dark';
    applyTheme(theme);
    set({ theme });
  },
  toggleFocus: () => set((s) => ({ focusMode: !s.focusMode })),
  setModal: (modal) => set({ modal }),
  setPalette: (open) => set({ paletteOpen: open }),
  toggleGraph: () => set((s) => ({ graphOpen: !s.graphOpen })),
  setAssistant: (open) => set({ assistantOpen: open }),
  toggleAssistant: () => set((s) => ({ assistantOpen: !s.assistantOpen })),
}));
