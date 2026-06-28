import type { ReactNode } from 'react';
import { useTranslation } from 'react-i18next';
import { Backdrop } from '@/components/Backdrop';
import { Topbar } from './Topbar';
import { ImpersonationBanner } from './ImpersonationBanner';

export function Shell({ children }: { children: ReactNode }) {
  const { t } = useTranslation();
  return (
    <div className="flex h-screen w-screen flex-col overflow-hidden">
      {/* Keyboard skip link (WCAG 2.4.1) — first in tab order, visible on focus
          so keyboard users can jump past the sticky nav to the page content. */}
      <a
        href="#main-content"
        className="sr-only rounded-lg border brd bg-[var(--surface-1)] px-4 py-2 text-[13px] font-semibold t-primary shadow-[var(--shadow-pop)] focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50"
      >
        {t('a11y.skip')}
      </a>
      <Backdrop />
      <ImpersonationBanner />
      <Topbar />
      <main id="main-content" className="flex-1 overflow-y-auto overflow-x-hidden">
        <div className="mx-auto w-full max-w-[1400px] px-4 py-5 sm:px-6 lg:px-8 lg:py-7">
          {children}
        </div>
      </main>
    </div>
  );
}
