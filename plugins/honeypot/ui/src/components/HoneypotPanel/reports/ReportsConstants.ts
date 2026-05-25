import {
  FileText,
  Shield,
  AlertTriangle,
  Target,
  Network,
  Globe,
  BarChart3,
  Bug,
  CheckCircle,
  List,
  Clock,
  Building,
  FileCode,
  Microscope,
  BookOpen,
  Crosshair,
  TrendingUp,
  FileSearch,
} from 'lucide-react';
import type { ReportType, ReportSection } from '../../types';

// Report type icons
export const REPORT_TYPE_ICONS: Record<ReportType, React.ElementType> = {
  executive: Building,
  technical: FileCode,
  compliance: Shield,
  incident: AlertTriangle,
  pentest: Target,
  threat_intel: Network,
  research: Microscope,
};

// Section icons
export const SECTION_ICONS: Record<ReportSection, React.ElementType> = {
  executive_summary: FileText,
  threat_landscape: Globe,
  attack_analytics: BarChart3,
  geo_analysis: Globe,
  botnet_discovery: Bug,
  pentest_results: Target,
  cve_correlations: Shield,
  recommendations: CheckCircle,
  ioc_list: List,
  timeline: Clock,
  // Research-specific sections
  abstract: BookOpen,
  key_findings: FileSearch,
  mitre_mapping: Crosshair,
  statistical_analysis: TrendingUp,
  payload_analysis: FileCode,
};

// Time range options
export const TIME_RANGES = [
  { value: 24, label: 'Last 24 Hours' },
  { value: 72, label: 'Last 3 Days' },
  { value: 168, label: 'Last 7 Days' },
  { value: 336, label: 'Last 14 Days' },
  { value: 720, label: 'Last 30 Days' },
  { value: 8760, label: 'All Time (1 Year)' },
];

// Default sections per report type
export const DEFAULT_SECTIONS: Record<ReportType, ReportSection[]> = {
  executive: ['executive_summary', 'threat_landscape', 'recommendations'],
  technical: [
    'executive_summary',
    'attack_analytics',
    'geo_analysis',
    'timeline',
    'ioc_list',
    'recommendations',
  ],
  compliance: ['executive_summary', 'attack_analytics', 'pentest_results', 'recommendations'],
  incident: ['executive_summary', 'timeline', 'attack_analytics', 'ioc_list', 'recommendations'],
  pentest: ['executive_summary', 'pentest_results', 'cve_correlations', 'recommendations'],
  threat_intel: [
    'executive_summary',
    'threat_landscape',
    'botnet_discovery',
    'geo_analysis',
    'ioc_list',
    'recommendations',
  ],
  research: [
    'abstract',
    'key_findings',
    'mitre_mapping',
    'statistical_analysis',
    'payload_analysis',
    'geo_analysis',
    'botnet_discovery',
    'recommendations',
  ],
};
