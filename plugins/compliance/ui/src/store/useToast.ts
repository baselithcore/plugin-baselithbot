import { create } from 'zustand';

export interface Toast {
  id: number;
  text: string;
  tone: 'ok' | 'err';
}

interface ToastState {
  toasts: Toast[];
  push: (text: string, tone?: 'ok' | 'err') => void;
  dismiss: (id: number) => void;
}

let seq = 0;

export const useToast = create<ToastState>((set) => ({
  toasts: [],
  push: (text, tone = 'ok') => {
    const id = ++seq;
    set((s) => ({ toasts: [...s.toasts, { id, text, tone }] }));
    setTimeout(() => set((s) => ({ toasts: s.toasts.filter((t) => t.id !== id) })), 4000);
  },
  dismiss: (id) => set((s) => ({ toasts: s.toasts.filter((t) => t.id !== id) })),
}));
