'use client';

import { useEffect } from 'react';
import { NextIntlClientProvider } from 'next-intl';
import { useLocaleStore } from '@/lib/i18n/store';
import { MESSAGES } from '@/lib/i18n/messages';

export function IntlProvider({ children }: { children: React.ReactNode }) {
  const locale = useLocaleStore((s) => s.locale);

  useEffect(() => {
    if (typeof document !== 'undefined') {
      document.documentElement.lang = locale;
    }
  }, [locale]);

  return (
    <NextIntlClientProvider
      locale={locale}
      messages={MESSAGES[locale]}
      timeZone="Europe/Rome"
      now={new Date()}
    >
      {children}
    </NextIntlClientProvider>
  );
}
