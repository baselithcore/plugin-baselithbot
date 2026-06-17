import { GitBranch, LogOut, Plus, Search, Workflow } from 'lucide-react';
import { useMemo, useState } from 'react';
import { useAuth } from '@auth';

import type { ProcessGraph } from '../api/types';
import { cn } from '../lib/ui';

interface SidebarProps {
  processes: ProcessGraph[];
  selectedId: string | null;
  loading: boolean;
  onSelect: (id: string) => void;
  onCreate: () => void;
}

/** Left rail: brand, process list, and the create action. */
export function Sidebar({ processes, selectedId, loading, onSelect, onCreate }: SidebarProps) {
  const { user, logout } = useAuth();
  const [query, setQuery] = useState('');
  const filtered = useMemo(() => {
    const needle = query.trim().toLowerCase();
    if (!needle) return processes;
    return processes.filter((p) =>
      [p.id, p.name, p.description].some((value) => value.toLowerCase().includes(needle))
    );
  }, [processes, query]);

  const totalSteps = processes.reduce((sum, p) => sum + p.nodes.length, 0);
  const totalKpis = processes.reduce((sum, p) => sum + p.kpis.length, 0);

  return (
    <aside className="flex max-h-72 w-full shrink-0 flex-col gap-4 overflow-hidden border-b border-white/10 bg-ink-950/80 p-4 backdrop-blur-xl lg:h-full lg:max-h-none lg:w-[18.5rem] lg:border-b-0 lg:border-r">
      <div className="flex items-center gap-3 px-1">
        <div
          className="grid h-10 w-10 place-items-center rounded-xl border border-accent/25 bg-gradient-to-br from-accent-deep/25 to-iris-deep/15 text-accent-soft shadow-[0_8px_24px_-12px_rgba(56,189,248,0.6)]"
          translate="no"
        >
          <Workflow size={20} strokeWidth={2.2} aria-hidden="true" />
        </div>
        <div className="min-w-0 flex-1 leading-tight">
          <p className="truncate text-sm font-semibold tracking-tight text-slate-100">
            Process Optimizer
          </p>
          <p className="truncate text-[11px] text-slate-500">Operations intelligence</p>
        </div>
        {user && (
          <div className="flex shrink-0 items-center gap-2">
            <span
              className="max-w-[7rem] truncate text-[11px] font-medium text-slate-400"
              title={user.username || user.email}
            >
              {user.username || user.email}
            </span>
            <button
              type="button"
              onClick={() => void logout()}
              title="Logout"
              aria-label="Logout"
              className="grid h-7 w-7 place-items-center rounded-lg border border-white/10 text-slate-400 transition-colors hover:border-white/20 hover:bg-white/[0.06] hover:text-slate-200"
            >
              <LogOut size={14} aria-hidden="true" />
            </button>
          </div>
        )}
      </div>

      <button className="btn-primary w-full justify-center" onClick={onCreate}>
        <Plus size={16} strokeWidth={2.4} aria-hidden="true" />
        New Process
      </button>

      <div className="relative">
        <Search
          size={15}
          className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-slate-500"
          aria-hidden="true"
        />
        <input
          className="field pl-9"
          name="process-search"
          autoComplete="off"
          aria-label="Search processes"
          placeholder="Search processes…"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
        />
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto pr-1">
        <div className="mb-2 flex items-center justify-between px-1">
          <p className="section-title">Processes</p>
          <span className="number text-[11px] text-slate-500">{processes.length}</span>
        </div>
        {loading ? (
          <div className="space-y-1.5">
            {[0, 1, 2].map((i) => (
              <div key={i} className="skeleton h-14 w-full" />
            ))}
          </div>
        ) : processes.length === 0 ? (
          <div className="glass p-3.5 text-xs text-slate-500">
            <p className="font-medium text-slate-300">No processes yet</p>
            <p className="mt-1 leading-relaxed">
              Create one visually, import BPMN/XML, or mine an event log.
            </p>
          </div>
        ) : filtered.length === 0 ? (
          <p className="px-1 py-4 text-center text-xs text-slate-500">No matching processes.</p>
        ) : (
          <ul className="space-y-1">
            {filtered.map((p) => {
              const active = selectedId === p.id;
              return (
                <li key={p.id}>
                  <button
                    onClick={() => onSelect(p.id)}
                    aria-current={active ? 'true' : undefined}
                    className={cn(
                      'group relative w-full rounded-lg border px-3 py-2.5 pl-3.5 text-left text-sm transition-colors',
                      active
                        ? 'border-accent/30 bg-accent/[0.08] text-accent-soft'
                        : 'border-transparent text-slate-300 hover:border-white/10 hover:bg-white/[0.05]'
                    )}
                  >
                    {active && (
                      <span className="absolute inset-y-2 left-0 w-0.5 rounded-full bg-accent" />
                    )}
                    <span className="block truncate font-medium">{p.name}</span>
                    <span className="mt-1 flex items-center gap-2 text-[11px] text-slate-500">
                      <span className="number">{p.nodes.length} steps</span>
                      <span className="h-1 w-1 rounded-full bg-slate-700" aria-hidden="true" />
                      <span className="number">{p.kpis.length} KPIs</span>
                    </span>
                  </button>
                </li>
              );
            })}
          </ul>
        )}
      </div>

      <div className="grid grid-cols-2 gap-2 border-t border-white/10 pt-3">
        <FootStat icon={<Workflow size={13} />} label="Steps" value={totalSteps} />
        <FootStat icon={<GitBranch size={13} />} label="KPIs" value={totalKpis} />
      </div>
    </aside>
  );
}

function FootStat({ icon, label, value }: { icon: React.ReactNode; label: string; value: number }) {
  return (
    <div className="flex items-center gap-2 rounded-lg bg-white/[0.02] px-2.5 py-2">
      <span className="text-slate-500" aria-hidden="true">
        {icon}
      </span>
      <div className="min-w-0 leading-tight">
        <p className="number text-sm font-semibold text-slate-200">{value}</p>
        <p className="truncate text-[10px] uppercase tracking-wide text-slate-500">{label}</p>
      </div>
    </div>
  );
}
