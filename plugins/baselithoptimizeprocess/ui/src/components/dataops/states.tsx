import type { ReactNode } from 'react';

/**
 * Shared loading + empty states for the insight panels, so every panel uses the
 * same shimmer skeleton and empty-state treatment as the rest of the dashboard
 * (matching the Sidebar) instead of bare "Loading…" text.
 */

/** Shimmer skeleton standing in for a panel while its data loads. */
export function PanelLoader({ rows = 3 }: { rows?: number }) {
  return (
    <div className="space-y-4" aria-busy="true" aria-live="polite">
      <span className="sr-only">Loading…</span>
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {[0, 1, 2, 3].map((i) => (
          <div key={i} className="skeleton h-16 w-full" />
        ))}
      </div>
      <div className="space-y-2">
        {Array.from({ length: rows }, (_, i) => (
          <div key={i} className="skeleton h-14 w-full" />
        ))}
      </div>
    </div>
  );
}

/** Friendly empty/no-data state with a title and guidance. */
export function PanelEmpty({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="glass p-6 text-sm text-slate-400">
      <p className="font-medium text-slate-200">{title}</p>
      <p className="mt-1 max-w-2xl leading-relaxed">{children}</p>
    </div>
  );
}
