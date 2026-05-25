"use client";

import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";
import { DEFAULT_LOCALE, STORAGE_KEY, type Locale, isLocale } from "./config";

interface LocaleState {
  locale: Locale;
  setLocale: (l: Locale) => void;
}

export const useLocaleStore = create<LocaleState>()(
  persist(
    (set) => ({
      locale: DEFAULT_LOCALE,
      setLocale: (locale) => set({ locale }),
    }),
    {
      name: STORAGE_KEY,
      storage: createJSONStorage(() => localStorage),
      partialize: (s) => ({ locale: s.locale }),
      merge: (persisted, current) => {
        const p = persisted as Partial<LocaleState> | undefined;
        return {
          ...current,
          locale: isLocale(p?.locale) ? p!.locale! : current.locale,
        };
      },
    },
  ),
);
