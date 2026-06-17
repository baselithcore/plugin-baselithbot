/**
 * i18n bootstrap (English default, Italian).
 *
 * English is the fallback; the user's choice is detected from localStorage /
 * the browser and persisted. Import this module once (side-effect) before the
 * app renders.
 */

import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import LanguageDetector from 'i18next-browser-languagedetector';

import en from '../locales/en/translation.json';
import it from '../locales/it/translation.json';

export const SUPPORTED_LANGUAGES = ['en', 'it'] as const;
export type Language = (typeof SUPPORTED_LANGUAGES)[number];

i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources: {
      en: { translation: en },
      it: { translation: it },
    },
    fallbackLng: 'en',
    supportedLngs: SUPPORTED_LANGUAGES as unknown as string[],
    interpolation: { escapeValue: false },
    detection: {
      order: ['localStorage', 'navigator'],
      lookupLocalStorage: 'baselith_lang',
      caches: ['localStorage'],
    },
  });

export default i18n;
