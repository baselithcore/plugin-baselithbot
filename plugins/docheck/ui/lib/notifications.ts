"use client";

import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";

export type NotificationTone = "info" | "success" | "warning" | "danger";

export interface NotificationItem {
  id: string;
  ts: number;
  tone: NotificationTone;
  title: string;
  body?: string;
  href?: string;
  source?: string;
  read: boolean;
}

interface NotificationsState {
  items: NotificationItem[];
  add: (n: Omit<NotificationItem, "id" | "ts" | "read">) => void;
  markAllRead: () => void;
  markRead: (id: string) => void;
  remove: (id: string) => void;
  clear: () => void;
}

const MAX_ITEMS = 50;

function makeId(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  return `${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
}

export const useNotifications = create<NotificationsState>()(
  persist(
    (set) => ({
      items: [],
      add: (n) =>
        set((s) => {
          const next: NotificationItem = {
            id: makeId(),
            ts: Date.now(),
            read: false,
            ...n,
          };
          // Dedupe: drop if identical title+body landed in last 3s.
          const recent = s.items[0];
          if (
            recent &&
            recent.title === next.title &&
            recent.body === next.body &&
            next.ts - recent.ts < 3000
          ) {
            return s;
          }
          return { items: [next, ...s.items].slice(0, MAX_ITEMS) };
        }),
      markAllRead: () =>
        set((s) => ({ items: s.items.map((i) => ({ ...i, read: true })) })),
      markRead: (id) =>
        set((s) => ({
          items: s.items.map((i) => (i.id === id ? { ...i, read: true } : i)),
        })),
      remove: (id) =>
        set((s) => ({ items: s.items.filter((i) => i.id !== id) })),
      clear: () => set({ items: [] }),
    }),
    {
      name: "docheck:notifications",
      storage: createJSONStorage(() =>
        typeof window === "undefined"
          ? (undefined as unknown as Storage)
          : window.localStorage,
      ),
      partialize: (s) => ({ items: s.items }),
    },
  ),
);

export function notify(n: Omit<NotificationItem, "id" | "ts" | "read">): void {
  useNotifications.getState().add(n);
}
