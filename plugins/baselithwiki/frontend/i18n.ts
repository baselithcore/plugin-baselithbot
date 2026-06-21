/**
 * i18n bootstrap for the BaselithWiki SPA (en + it).
 *
 * The wiki UI is grandfathered English-heavy; this layer wires the shared
 * react-i18next infrastructure for the shell + auth/access surfaces (language
 * switcher, access-denied, account menu) per the platform i18n mandate, with
 * `en` as the default/fallback and `it` complete in parallel. Deep wiki content
 * strings are migrated incrementally — add keys here in BOTH locales together.
 */

import i18n from 'i18next';
import LanguageDetector from 'i18next-browser-languagedetector';
import { initReactI18next } from 'react-i18next';

const en = {
  shell: {
    language: 'Language',
    account: 'Account',
    logout: 'Sign out',
    admin: 'Administration',
    embeds: 'Embeds',
    feedback: 'Feedback',
    accessDenied: 'Access denied',
    accessDeniedBody: 'You do not have permission to view this section.',
    loading: 'Loading…',
  },
} as const;

const it = {
  shell: {
    language: 'Lingua',
    account: 'Account',
    logout: 'Esci',
    admin: 'Amministrazione',
    embeds: 'Widget',
    feedback: 'Feedback',
    accessDenied: 'Accesso negato',
    accessDeniedBody: 'Non hai i permessi per visualizzare questa sezione.',
    loading: 'Caricamento…',
  },
} as const;

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
      lookupLocalStorage: 'i18nextLng',
      caches: ['localStorage'],
    },
  });

export default i18n;
