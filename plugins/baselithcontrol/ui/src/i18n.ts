import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import en from './locales/en/common.json';
import it from './locales/it/common.json';

const STORAGE_KEY = 'blc.lang';

void i18n.use(initReactI18next).init({
  resources: { en: { common: en }, it: { common: it } },
  lng: localStorage.getItem(STORAGE_KEY) ?? 'en',
  fallbackLng: 'en',
  defaultNS: 'common',
  interpolation: { escapeValue: false },
});

export function setLanguage(lang: 'en' | 'it'): void {
  localStorage.setItem(STORAGE_KEY, lang);
  void i18n.changeLanguage(lang);
}

export default i18n;
