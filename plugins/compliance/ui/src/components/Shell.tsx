import type { ReactNode } from 'react';

import { api } from '../lib/api';
import { useApi } from '../lib/useApi';
import { Sidebar } from './Sidebar';
import { Topbar } from './Topbar';
import { Toaster } from './Toaster';

export function Shell({ children }: { children: ReactNode }) {
  // Lightweight poll for the sidebar overdue badge (the headline GRC signal).
  const { data } = useApi(() => api.overview());
  const overdue = (data?.nis2.overdue ?? 0) + (data?.dora.overdue ?? 0);

  return (
    <div className="console">
      <Sidebar overdue={overdue} />
      <div className="console-shell">
        <Topbar />
        <main className="main">{children}</main>
      </div>
      <Toaster />
    </div>
  );
}
