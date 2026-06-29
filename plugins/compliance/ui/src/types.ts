// Wire types mirroring the compliance backend payloads (subset used by the UI).

export type TabId = 'overview' | 'incidents' | 'dora' | 'dsr' | 'thirdparty' | 'transparency';

export interface Deadline {
  regime: 'nis2' | 'dora';
  incident_id: string;
  title: string;
  kind: string;
  due_at: string;
  overdue: boolean;
}

export interface Overview {
  nis2: { total: number; open: number; overdue: number };
  dora: { total: number; open: number; overdue: number; major: number };
  dsr: { providers: number };
  thirdparty: { providers: number; arrangements: number; critical: number; flags: number };
  transparency: { enabled: boolean; should_disclose: boolean };
  deadlines: Deadline[];
}

export interface Milestone {
  kind: string;
  due_at: string;
  submitted: boolean;
  overdue: boolean;
}

export interface Incident {
  id: string;
  title: string;
  severity: string;
  status: string;
  significant?: boolean;
  is_major?: boolean;
  description: string;
  detected_at: string;
  milestones: Milestone[];
}

export interface IncidentList {
  incidents: Incident[];
  overdue_count: number;
}

export interface Provider {
  id: string;
  name: string;
  country: string | null;
  provider_type: string;
  is_critical_designated: boolean;
}

export interface ICTFunction {
  id: string;
  name: string;
  criticality: string;
}

export interface Arrangement {
  reference_number: string;
  provider_id: string;
  function_ids: string[];
  assessment: { supports_critical_function: boolean; substitutability: string };
}

export interface Concentration {
  providers: number;
  arrangements: number;
  critical_or_important_arrangements: number;
  concentration_flags: {
    provider_id: string;
    reference_number: string;
    substitutability: string;
  }[];
}

export interface TransparencyStatus {
  enabled: boolean;
  should_disclose: boolean;
  notice: Record<string, unknown> | null;
}

export interface SubjectExport {
  subject_id: string;
  data: Record<string, unknown>;
}

export interface ErasureReport {
  subject_id: string;
  erased: Record<string, number>;
  total: number;
}
