import {
  AlertTriangle,
  Download,
  Gauge,
  Layers,
  Pencil,
  Radio,
  Sparkles,
  Trash2,
} from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';

import { api } from '../api/client';
import type { Bottleneck, KpiSnapshot, OptimizationProposal, ProcessGraph } from '../api/types';
import { cn, severityRank } from '../lib/ui';
import { AnalyticsPanel } from './dataops/AnalyticsPanel';
import { AutomationPanel } from './dataops/AutomationPanel';
import { ConformancePanel } from './dataops/ConformancePanel';
import { CostPanel } from './dataops/CostPanel';
import { ForecastPanel } from './dataops/ForecastPanel';
import { GovernancePanel } from './dataops/GovernancePanel';
import { PerformancePanel } from './dataops/PerformancePanel';
import { PredictPanel } from './dataops/PredictPanel';
import { ResourcesPanel } from './dataops/ResourcesPanel';
import { RootCausePanel } from './dataops/RootCausePanel';
import { VariantPanel } from './dataops/VariantPanel';
import { BottleneckList } from './BottleneckList';
import { KpiMonitor } from './KpiMonitor';
import { MetricInjector } from './MetricInjector';
import { ProcessFlow } from './ProcessFlow';
import { ProposalsPanel } from './ProposalsPanel';
import { StatStrip, type StatItem } from './workspace/StatStrip';
import { TabBar } from './workspace/TabBar';
import { PLUGIN, TABS, type Tab } from './workspace/types';
import { useAuth } from '@auth';

/** Fetch a Markdown report and trigger a browser download. */
async function exportReport(processId: string): Promise<void> {
  const text = await api.report(processId, 'markdown');
  const url = URL.createObjectURL(new Blob([text], { type: 'text/markdown' }));
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = `${processId}-report.md`;
  anchor.click();
  URL.revokeObjectURL(url);
}

interface ProcessWorkspaceProps {
  process: ProcessGraph;
  snapshots: KpiSnapshot[];
  bottlenecks: Bottleneck[];
  connected: boolean;
  proposals: OptimizationProposal[];
  optimizing: boolean;
  onOptimize: () => void;
  onDecision: (updated: OptimizationProposal) => void;
  onDelete: () => void;
  onEdit: () => void;
}

export function ProcessWorkspace(props: ProcessWorkspaceProps) {
  const { process, snapshots, bottlenecks, connected } = props;
  const { canAccessTab } = useAuth();
  const [tab, setTab] = useState<Tab>(() => {
    const fromUrl = new URLSearchParams(window.location.search).get('tab');
    if (TABS.some((item) => item.id === fromUrl)) return fromUrl as Tab;
    return 'map';
  });

  // Keep the active section legal: if the central RBAC policy denies it, fall
  // back to the first accessible section (default-allow when unmanaged).
  useEffect(() => {
    if (canAccessTab(tab, PLUGIN)) return;
    const fallback = TABS.find((t) => canAccessTab(t.id, PLUGIN));
    if (fallback && fallback.id !== tab) setTab(fallback.id);
  }, [tab, canAccessTab]);

  const hasMetrics = snapshots.some((snapshot) => snapshot.sample_count > 0);
  const breachingCount = snapshots.filter((snapshot) => snapshot.breaching).length;
  const pendingProposals = props.proposals.filter((p) => p.status === 'proposed').length;
  const worstBottleneck = useMemo(
    () =>
      [...bottlenecks].sort((a, b) => severityRank[b.severity] - severityRank[a.severity])[0] ??
      null,
    [bottlenecks]
  );

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    params.set('tab', tab);
    window.history.replaceState(null, '', `${window.location.pathname}?${params.toString()}`);
  }, [tab]);

  const stats: StatItem[] = [
    {
      label: 'Steps',
      value: process.nodes.length,
      detail: `${process.edges.length} links`,
      icon: Layers,
    },
    {
      label: 'KPI Breaches',
      value: breachingCount,
      tone: breachingCount ? 'critical' : 'good',
      detail: `${process.kpis.length} tracked`,
      icon: Gauge,
    },
    {
      label: 'Bottlenecks',
      value: bottlenecks.length,
      tone:
        worstBottleneck?.severity === 'critical'
          ? 'critical'
          : bottlenecks.length
            ? 'warning'
            : 'good',
      detail: worstBottleneck ? `worst: ${worstBottleneck.severity}` : 'none active',
      icon: AlertTriangle,
    },
    {
      label: 'Proposals',
      value: pendingProposals,
      tone: pendingProposals ? 'accent' : 'neutral',
      detail: `${props.proposals.length} total`,
      icon: Sparkles,
    },
    {
      label: 'Metric Feed',
      value: hasMetrics ? 'Ready' : 'Empty',
      tone: hasMetrics ? 'good' : 'neutral',
      detail: connected ? 'streaming' : 'not connected',
      icon: Radio,
    },
  ];

  return (
    <div className="flex h-full flex-col overflow-hidden">
      <header className="border-b border-white/10 bg-ink-950/40 px-6 py-4 backdrop-blur-sm">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2.5">
              <h1 className="min-w-0 truncate text-xl font-semibold tracking-tight text-slate-50">
                {process.name}
              </h1>
              <span
                className={cn(
                  'chip',
                  connected ? 'bg-sev-low/12 text-sev-low' : 'bg-white/[0.05] text-slate-400'
                )}
              >
                <span
                  className={cn(
                    'h-1.5 w-1.5 rounded-full',
                    connected ? 'animate-pulse bg-sev-low' : 'bg-slate-500'
                  )}
                />
                {connected ? 'Live' : 'Idle'}
              </span>
            </div>
            <p className="mt-1 max-w-3xl text-sm text-slate-400">
              {process.description ||
                `${process.nodes.length} mapped steps with ${process.kpis.length} tracked KPIs`}
            </p>
          </div>
          <div className="flex shrink-0 items-center gap-2">
            <button className="btn-ghost" onClick={() => void exportReport(process.id)}>
              <Download size={16} aria-hidden="true" />
              <span className="hidden sm:inline">Export</span>
            </button>
            <button className="btn-ghost" onClick={props.onEdit}>
              <Pencil size={16} aria-hidden="true" />
              <span className="hidden sm:inline">Edit Map</span>
            </button>
            <button className="btn-danger" onClick={props.onDelete} aria-label="Delete process">
              <Trash2 size={16} aria-hidden="true" />
            </button>
          </div>
        </div>

        <StatStrip stats={stats} />
        <TabBar active={tab} onChange={setTab} />
      </header>

      <div key={tab} className="min-h-0 flex-1 animate-fade-in overflow-y-auto px-6 py-5">
        {tab === 'map' && (
          <div className="grid min-h-full grid-cols-1 gap-4 xl:grid-cols-[minmax(0,1fr)_24rem]">
            <div className="min-h-[520px]">
              <ProcessFlow process={process} bottlenecks={bottlenecks} />
            </div>
            <aside className="space-y-4">
              <PanelTitle title="Detected Bottlenecks" detail="Worst items are shown first." />
              <BottleneckList
                bottlenecks={bottlenecks}
                kpiCount={process.kpis.length}
                hasMetrics={hasMetrics}
              />
            </aside>
          </div>
        )}

        {tab === 'monitor' && (
          <div className="space-y-5">
            <MetricInjector processId={process.id} kpis={process.kpis} nodes={process.nodes} />
            <KpiMonitor kpis={process.kpis} snapshots={snapshots} connected={connected} />
            <ForecastPanel processId={process.id} />
            <BottleneckList
              bottlenecks={bottlenecks}
              kpiCount={process.kpis.length}
              hasMetrics={hasMetrics}
            />
          </div>
        )}

        {tab === 'analytics' && <AnalyticsPanel processId={process.id} />}

        {tab === 'variants' && <VariantPanel processId={process.id} />}

        {tab === 'performance' && <PerformancePanel processId={process.id} />}

        {tab === 'rootcause' && <RootCausePanel processId={process.id} />}

        {tab === 'predict' && <PredictPanel processId={process.id} />}

        {tab === 'conformance' && <ConformancePanel processId={process.id} />}

        {tab === 'optimize' && (
          <div className="space-y-4">
            <CostPanel processId={process.id} />
            <ProposalsPanel
              processId={process.id}
              proposals={props.proposals}
              busy={props.optimizing}
              onOptimize={props.onOptimize}
              onDecision={props.onDecision}
            />
          </div>
        )}

        {tab === 'resources' && <ResourcesPanel />}

        {tab === 'automation' && <AutomationPanel process={process} />}

        {tab === 'history' && <GovernancePanel processId={process.id} />}
      </div>
    </div>
  );
}

function PanelTitle({ title, detail }: { title: string; detail: string }) {
  return (
    <div>
      <h2 className="text-sm font-semibold text-slate-100">{title}</h2>
      <p className="mt-1 text-xs text-slate-500">{detail}</p>
    </div>
  );
}
