import type { ReactNode } from 'react';
import { Backdrop } from '@/components/Backdrop';
import { Topbar } from './Topbar';
import { ImpersonationBanner } from './ImpersonationBanner';

export function Shell({ children }: { children: ReactNode }) {
  return (
    <div className="flex h-screen w-screen flex-col overflow-hidden">
      <Backdrop />
      <ImpersonationBanner />
      <Topbar />
      <main className="flex-1 overflow-y-auto overflow-x-hidden">
        <div className="mx-auto w-full max-w-[1400px] px-4 py-5 sm:px-6 lg:px-8 lg:py-7">
          {children}
        </div>
      </main>
    </div>
  );
}
