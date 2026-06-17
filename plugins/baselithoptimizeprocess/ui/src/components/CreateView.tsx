import type { LucideIcon } from 'lucide-react';
import { Database, FileCode2, PenLine } from 'lucide-react';
import { useState } from 'react';

import type { ProcessGraph } from '../api/types';
import { cn } from '../lib/ui';
import { MineImport } from './dataops/MineImport';
import { ProcessEditor } from './editor/ProcessEditor';
import { XmlImport } from './XmlImport';

interface CreateViewProps {
  onCreated: (process: ProcessGraph) => void;
}

type Mode = 'visual' | 'mine' | 'xml';

const MODES: { id: Mode; label: string; detail: string; icon: LucideIcon }[] = [
  {
    id: 'visual',
    label: 'Visual Editor',
    detail: 'Draw steps, KPIs and costs manually',
    icon: PenLine,
  },
  { id: 'mine', label: 'Mine From Log', detail: 'Discover flow from event data', icon: Database },
  {
    id: 'xml',
    label: 'BPMN / XML Import',
    detail: 'Start from an existing model',
    icon: FileCode2,
  },
];

/** Landing view to map a new process — visual editor or BPMN/XML import. */
export function CreateView({ onCreated }: CreateViewProps) {
  const [mode, setMode] = useState<Mode>('visual');

  return (
    <div className="flex h-full flex-col overflow-hidden">
      <header className="border-b border-white/10 bg-neutral-950/35 px-6 py-5">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h1 className="text-xl font-semibold text-slate-50">Create Process</h1>
            <p className="mt-1 text-sm text-slate-400">
              Choose the fastest path to a measurable process model.
            </p>
          </div>
        </div>
        <div className="mt-4 grid grid-cols-1 gap-2 md:grid-cols-3">
          {MODES.map((m) => {
            const active = mode === m.id;
            return (
              <button
                key={m.id}
                onClick={() => setMode(m.id)}
                className={cn(
                  'flex items-start gap-3 rounded-xl border px-4 py-3 text-left transition-colors',
                  active
                    ? 'border-accent/40 bg-accent/[0.08] text-accent-soft'
                    : 'border-white/10 bg-white/[0.025] text-slate-300 hover:border-white/20 hover:bg-white/[0.055]'
                )}
                aria-pressed={active}
              >
                <span
                  className={cn(
                    'grid h-9 w-9 shrink-0 place-items-center rounded-lg',
                    active ? 'bg-accent/15 text-accent-soft' : 'bg-white/[0.05] text-slate-400'
                  )}
                >
                  <m.icon size={18} aria-hidden="true" />
                </span>
                <span className="min-w-0">
                  <span className="block text-sm font-semibold">{m.label}</span>
                  <span className="mt-0.5 block text-xs text-slate-500">{m.detail}</span>
                </span>
              </button>
            );
          })}
        </div>
      </header>

      <div className="min-h-0 flex-1 overflow-y-auto">
        {mode === 'visual' ? (
          <ProcessEditor onSaved={onCreated} />
        ) : mode === 'mine' ? (
          <div className="mx-auto max-w-3xl p-6">
            <MineImport onMined={onCreated} />
          </div>
        ) : (
          <div className="mx-auto max-w-3xl p-6">
            <XmlImport onImported={onCreated} />
          </div>
        )}
      </div>
    </div>
  );
}
