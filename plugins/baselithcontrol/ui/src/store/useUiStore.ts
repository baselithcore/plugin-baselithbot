import { create } from 'zustand';
import type { Tone } from '@/lib/format';

export interface Toast {
  id: number;
  message: string;
  tone: Tone;
}

interface ConfirmRequest {
  message: string;
  resolve: (ok: boolean) => void;
}

interface UiStore {
  toasts: Toast[];
  pushToast: (message: string, tone?: Tone) => void;
  dismissToast: (id: number) => void;
  confirm: ConfirmRequest | null;
  ask: (message: string) => Promise<boolean>;
  resolveConfirm: (ok: boolean) => void;
}

let nextId = 1;

// Lightweight UI primitives: toast notifications + a promise-based confirm
// dialog, replacing the browser's native alert()/confirm() with accessible,
// themed, animated equivalents.
export const useUiStore = create<UiStore>((set, get) => ({
  toasts: [],
  pushToast: (message, tone = 'info') => {
    const id = nextId++;
    set((s) => ({ toasts: [...s.toasts, { id, message, tone }] }));
    window.setTimeout(() => get().dismissToast(id), 4000);
  },
  dismissToast: (id) => set((s) => ({ toasts: s.toasts.filter((t) => t.id !== id) })),
  confirm: null,
  ask: (message) =>
    new Promise<boolean>((resolve) => set(() => ({ confirm: { message, resolve } }))),
  resolveConfirm: (ok) => {
    const req = get().confirm;
    req?.resolve(ok);
    set(() => ({ confirm: null }));
  },
}));
