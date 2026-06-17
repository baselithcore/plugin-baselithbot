import { useEffect, useState } from 'react';
import { AnimatePresence, motion } from 'motion/react';
import { X, Network } from 'lucide-react';
import { useBrain } from '@/store';
import { api } from '@/lib/api';
import type { GraphData } from '@/lib/types';
import { cn } from '@/lib/cn';
import { GraphView, type GraphMode } from './graph/GraphView';

const EMPTY: GraphData = { nodes: [], edges: [] };

function initialMode(): GraphMode {
  return localStorage.getItem('bb-graph-mode') === '3d' ? '3d' : '2d';
}

/** Full-vault graph overlay with 2D/3D view switch. Click a node to open it. */
export function GraphPanel() {
  const open = useBrain((s) => s.graphOpen);
  const toggle = useBrain((s) => s.toggleGraph);
  const activeId = useBrain((s) => s.activeId);
  const openNote = useBrain((s) => s.openNote);
  const activeWorkspace = useBrain((s) => s.activeWorkspace);
  const [data, setData] = useState<GraphData>(EMPTY);
  const [size, setSize] = useState({ w: 800, h: 600 });
  const [mode, setMode] = useState<GraphMode>(initialMode);

  useEffect(() => {
    if (!open) return;
    api
      .graph({ tags: true, workspace: activeWorkspace })
      .then(setData)
      .catch(() => setData(EMPTY));
    const measure = () => setSize({ w: window.innerWidth - 80, h: window.innerHeight - 140 });
    measure();
    window.addEventListener('resize', measure);
    return () => window.removeEventListener('resize', measure);
  }, [open, activeWorkspace]);

  const pickMode = (m: GraphMode) => {
    setMode(m);
    localStorage.setItem('bb-graph-mode', m);
  };

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.2 }}
          className="fixed inset-0 z-40 flex flex-col bg-[var(--color-overlay)] backdrop-blur-md"
          onClick={toggle}
        >
          <motion.div
            initial={{ opacity: 0, scale: 0.96, y: 12 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.97, y: 8 }}
            transition={{ type: 'spring', stiffness: 320, damping: 30 }}
            onClick={(e) => e.stopPropagation()}
            className="bb-glass m-6 flex flex-1 flex-col overflow-hidden rounded-[var(--radius-lg)] shadow-2xl"
          >
            <div className="flex items-center justify-between border-b border-[var(--color-border)] px-5 py-3.5">
              <div className="flex items-center gap-2.5">
                <span className="bb-gradient flex size-7 items-center justify-center rounded-lg text-white">
                  <Network className="size-4" />
                </span>
                <div>
                  <h2 className="text-sm font-semibold">Knowledge graph</h2>
                  <p className="text-xs text-[var(--color-faint)]">
                    {data.nodes.length} nodes · {data.edges.length} links — click to open
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <ModeToggle mode={mode} onPick={pickMode} />
                <button
                  onClick={toggle}
                  className="rounded-lg p-1.5 text-[var(--color-muted)] hover:bg-[var(--color-elevated)]"
                >
                  <X className="size-4" />
                </button>
              </div>
            </div>
            <div className="flex-1 overflow-hidden">
              <GraphView
                mode={mode}
                data={data}
                activeId={activeId}
                width={size.w}
                height={size.h}
                onNode={(id) => {
                  if (!id.startsWith('tag:')) {
                    void openNote(id);
                    toggle();
                  }
                }}
              />
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

function ModeToggle({ mode, onPick }: { mode: GraphMode; onPick: (m: GraphMode) => void }) {
  return (
    <div className="relative flex rounded-lg border border-[var(--color-border)] p-0.5 text-xs">
      {(['2d', '3d'] as GraphMode[]).map((m) => (
        <button
          key={m}
          onClick={() => onPick(m)}
          className={cn(
            'relative rounded-md px-2.5 py-1 font-medium uppercase transition-colors',
            mode === m ? 'text-white' : 'text-[var(--color-muted)] hover:text-[var(--color-text)]'
          )}
        >
          {mode === m && (
            <motion.span
              layoutId="graph-mode"
              className="bb-gradient absolute inset-0 -z-10 rounded-md"
              transition={{ type: 'spring', stiffness: 400, damping: 32 }}
            />
          )}
          {m}
        </button>
      ))}
    </div>
  );
}
