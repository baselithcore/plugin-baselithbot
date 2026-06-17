import { AlertTriangle, ShieldAlert } from 'lucide-react';
import { useCallback, useEffect, useState } from 'react';
import { useAuth } from '@auth';

import { api } from './api/client';
import type { OptimizationProposal, ProcessGraph } from './api/types';
import { CreateView } from './components/CreateView';
import { ProcessEditor } from './components/editor/ProcessEditor';
import { ProcessWorkspace } from './components/ProcessWorkspace';
import { Sidebar } from './components/Sidebar';
import { useLiveMetrics } from './hooks/useLiveMetrics';
import { PLUGIN, TABS } from './components/workspace/types';

export default function App() {
  const { canAccessTab } = useAuth();
  const [processes, setProcesses] = useState<ProcessGraph[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [editing, setEditing] = useState(false);
  const [proposals, setProposals] = useState<OptimizationProposal[]>([]);
  const [optimizing, setOptimizing] = useState(false);
  const [loading, setLoading] = useState(true);
  const [notice, setNotice] = useState<string | null>(null);

  const selected = processes.find((p) => p.id === selectedId) ?? null;
  const live = useLiveMetrics(creating || editing ? null : selectedId);

  const refreshProcesses = useCallback(async () => {
    const list = await api.listProcesses().catch(() => {
      setNotice('Process list unavailable. Check the plugin API and refresh.');
      return [];
    });
    setProcesses(list);
    setLoading(false);
    return list;
  }, []);

  useEffect(() => {
    void refreshProcesses().then((list) => {
      if (list.length && !selectedId) {
        setSelectedId(list[0].id);
        void api
          .listProposals(list[0].id)
          .then(setProposals)
          .catch(() => setProposals([]));
      }
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const selectProcess = useCallback((id: string) => {
    setNotice(null);
    setCreating(false);
    setEditing(false);
    setSelectedId(id);
    void api
      .listProposals(id)
      .then(setProposals)
      .catch(() => setProposals([]));
  }, []);

  const handleCreated = useCallback(
    async (process: ProcessGraph) => {
      await refreshProcesses();
      setNotice(null);
      setCreating(false);
      setEditing(false);
      setSelectedId(process.id);
      setProposals([]);
    },
    [refreshProcesses]
  );

  const optimize = useCallback(async () => {
    if (!selectedId) return;
    setOptimizing(true);
    setNotice(null);
    try {
      const fresh = await api.optimize(selectedId, '', 5);
      setProposals((prev) => [...fresh, ...prev]);
    } catch (e) {
      setNotice(e instanceof Error ? e.message : 'Optimizer failed.');
    } finally {
      setOptimizing(false);
    }
  }, [selectedId]);

  const handleDecision = useCallback((updated: OptimizationProposal) => {
    setProposals((prev) => prev.map((p) => (p.id === updated.id ? updated : p)));
  }, []);

  const deleteProcess = useCallback(async () => {
    if (!selectedId) return;
    const name = selected?.name ?? selectedId;
    if (!window.confirm(`Delete "${name}"? This removes the process and its optimization state.`)) {
      return;
    }
    await api.deleteProcess(selectedId).catch((e) => {
      setNotice(e instanceof Error ? e.message : 'Delete failed.');
    });
    const list = await refreshProcesses();
    setSelectedId(list[0]?.id ?? null);
    setProposals([]);
  }, [selected?.name, selectedId, refreshProcesses]);

  // Central RBAC gate: deny only when EVERY workspace section is restricted for
  // this caller. Default-allow per tab (unmanaged/unknown policy stays open), so
  // normal, unauthenticated use is never blocked.
  const anyTabAllowed = TABS.some((t) => canAccessTab(t.id, PLUGIN));
  if (!anyTabAllowed) {
    return (
      <div className="grid h-screen w-screen place-items-center bg-neutral-950/40 p-6 text-center">
        <div className="glass max-w-sm p-8">
          <ShieldAlert size={28} className="mx-auto text-sev-medium" aria-hidden="true" />
          <p className="mt-3 text-sm font-semibold text-slate-100">Access denied</p>
          <p className="mt-1.5 text-xs leading-relaxed text-slate-500">
            Your account doesn&apos;t have permission to view the Process Optimizer.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-screen w-screen flex-col overflow-hidden bg-neutral-950/40 lg:flex-row">
      <Sidebar
        processes={processes}
        selectedId={creating ? null : selectedId}
        loading={loading}
        onSelect={selectProcess}
        onCreate={() => {
          setNotice(null);
          setEditing(false);
          setCreating(true);
        }}
      />
      <main className="min-h-0 min-w-0 flex-1 overflow-hidden">
        {notice && (
          <div
            className="flex items-center gap-2 border-b border-sev-medium/25 bg-sev-medium/10 px-6 py-2.5 text-sm text-sev-medium"
            aria-live="polite"
          >
            <AlertTriangle size={15} className="shrink-0" aria-hidden="true" />
            {notice}
          </div>
        )}
        {editing && selected ? (
          <ProcessEditor
            initial={selected}
            onSaved={handleCreated}
            onCancel={() => setEditing(false)}
          />
        ) : creating || !selected ? (
          <CreateView onCreated={handleCreated} />
        ) : (
          <ProcessWorkspace
            process={selected}
            snapshots={live.snapshots}
            bottlenecks={live.bottlenecks}
            connected={live.connected}
            proposals={proposals}
            optimizing={optimizing}
            onOptimize={optimize}
            onDecision={handleDecision}
            onDelete={deleteProcess}
            onEdit={() => setEditing(true)}
          />
        )}
      </main>
    </div>
  );
}
