'use client';

import { Sidebar } from './Sidebar';

export function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="h-screen flex bg-bg-canvas text-text-primary">
      <Sidebar />
      <div className="flex-1 min-w-0 flex flex-col overflow-hidden">{children}</div>
    </div>
  );
}
