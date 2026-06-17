import type { LucideIcon } from 'lucide-react';
import {
  Activity,
  BarChart3,
  Crosshair,
  GitBranch,
  History,
  Map as MapIcon,
  Radar,
  ShieldCheck,
  Sparkles,
  Timer,
  Users,
  Workflow,
} from 'lucide-react';

export type Tab =
  | 'map'
  | 'monitor'
  | 'analytics'
  | 'variants'
  | 'performance'
  | 'rootcause'
  | 'predict'
  | 'conformance'
  | 'optimize'
  | 'resources'
  | 'automation'
  | 'history';

export interface TabDef {
  id: Tab;
  label: string;
  detail: string;
  icon: LucideIcon;
}

/** Plugin id — must match get_ui_tabs()[].plugin (metadata.name) for RBAC. */
export const PLUGIN = 'baselithoptimizeprocess';

export const TABS: TabDef[] = [
  { id: 'map', label: 'Map', detail: 'Structure and bottlenecks', icon: MapIcon },
  { id: 'monitor', label: 'Monitor', detail: 'Samples, forecasts and KPI health', icon: Activity },
  { id: 'analytics', label: 'Analyze', detail: 'Mining variants and throughput', icon: BarChart3 },
  { id: 'variants', label: 'Variants', detail: 'Path explorer and conformance', icon: GitBranch },
  {
    id: 'performance',
    label: 'Performance',
    detail: 'Throughput percentiles and SLAs',
    icon: Timer,
  },
  {
    id: 'rootcause',
    label: 'Root Cause',
    detail: 'Why cases run slow',
    icon: Crosshair,
  },
  { id: 'predict', label: 'Predict', detail: 'Forecast a running case', icon: Radar },
  { id: 'conformance', label: 'Conform', detail: 'Reality vs model', icon: ShieldCheck },
  { id: 'optimize', label: 'Optimize', detail: 'Cost, ROI and proposals', icon: Sparkles },
  { id: 'resources', label: 'Resources', detail: 'Pool, roles and rates', icon: Users },
  { id: 'automation', label: 'Automate', detail: 'Rules and firings', icon: Workflow },
  { id: 'history', label: 'Govern', detail: 'Versions, audit and rollback', icon: History },
];
