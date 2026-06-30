// i18n setup — English (default/fallback) + Italian, per the plugin convention.
// Locale is detected from localStorage ('bb-lang') then the browser, and
// persisted on change. Import this once (main.tsx) before rendering the app.
import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import LanguageDetector from 'i18next-browser-languagedetector';
import en from './locales/en.json';
import it from './locales/it.json';

export const SUPPORTED = [
  { code: 'en', label: 'English' },
  { code: 'it', label: 'Italiano' },
] as const;

void i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources: {
      en: { translation: en },
      it: { translation: it },
    },
    fallbackLng: 'en',
    supportedLngs: ['en', 'it'],
    interpolation: { escapeValue: false },
    detection: {
      order: ['localStorage', 'navigator'],
      lookupLocalStorage: 'bb-lang',
      caches: ['localStorage'],
    },
  });

export default i18n;
