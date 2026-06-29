import i18next from 'i18next';
import { initReactI18next } from 'react-i18next';

import en from './locales/en/common.json';
import it from './locales/it/common.json';

const STORAGE_KEY = 'comp.lang';

function initialLanguage(): 'en' | 'it' {
  const saved = localStorage.getItem(STORAGE_KEY);
  if (saved === 'en' || saved === 'it') return saved;
  return navigator.language.toLowerCase().startsWith('it') ? 'it' : 'en';
}

void i18next.use(initReactI18next).init({
  resources: { en: { common: en }, it: { common: it } },
  lng: initialLanguage(),
  fallbackLng: 'en',
  defaultNS: 'common',
  // Flat catalog keys (e.g. "app.title") — do not treat "." as a path.
  keySeparator: false,
  nsSeparator: false,
  interpolation: { escapeValue: false },
});

export function setLanguage(lang: 'en' | 'it'): void {
  localStorage.setItem(STORAGE_KEY, lang);
  void i18next.changeLanguage(lang);
}

export default i18next;
