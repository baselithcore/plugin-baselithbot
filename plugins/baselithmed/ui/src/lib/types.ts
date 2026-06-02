export type TriageCode = 'RED' | 'YELLOW' | 'GREEN' | 'WHITE';

export type ReportStatus = 'DRAFT' | 'PENDING_VALIDATION' | 'VALIDATED' | 'REJECTED';

export interface Symptom {
  canonical_name: string;
  raw_quote: string;
  body_site: string | null;
  onset: string | null;
  severity_nrs: number | null;
  character: string[];
  icd10_hint: string | null;
  source_turn_id: string;
}

export interface TemporalLink {
  source: string;
  target: string;
  relation: 'PRECEDES' | 'COOCCURS' | 'AGGRAVATES' | 'RELIEVES';
  delta_minutes: number | null;
}

export interface SymptomMatrix {
  symptoms: Symptom[];
  temporal_sequence: TemporalLink[];
  red_flags: string[];
  denied_symptoms?: string[];
  medications?: string[];
  allergies?: string[];
  past_medical_history?: string[];
}

export interface DifferentialHypothesis {
  condition: string;
  icd10: string | null;
  confidence: number;
  p_value_simulated: number | null;
  supporting_findings: string[];
  contradicting_findings: string[];
  recommended_workup: string[];
}

export interface DifferentialDiagnosis {
  hypotheses: DifferentialHypothesis[];
  model_id: string;
  generated_at: string;
  notes: string | null;
}

export interface TriageDecision {
  code: TriageCode;
  target_latency_minutes: number;
  rationale: string;
  red_flag_overrides: string[];
}

export interface TriageReport {
  session_id: string;
  patient_pseudonym: string;
  generated_at: string;
  symptom_matrix: SymptomMatrix;
  differential: DifferentialDiagnosis;
  triage: TriageDecision;
  disclaimer: string;
  status: ReportStatus;
  validation_request_id: string | null;
  validator_signature: string | null;
  intake_report?: string | null;
}

export interface LivePreview {
  is_preview: true;
  differential: DifferentialDiagnosis;
  triage: TriageDecision;
  symptom_count: number;
  red_flag_count: number;
  denied_symptoms?: string[];
  intake_report?: string | null;
}

export interface InterviewTurnResult {
  success: boolean;
  data: {
    session_id: string;
    question?: string;
    target_slot?: string;
    tone?: string;
    rationale?: string;
    progress?: number;
    known_symptoms?: string[];
    matrix?: SymptomMatrix;
    preview?: LivePreview | null;
    escalate?: boolean;
    triage_code?: TriageCode;
    reason?: string;
    instruction?: string;
  };
  metadata?: Record<string, unknown>;
}

export interface ChatMessage {
  id: string;
  role: 'patient' | 'agent' | 'system';
  text: string;
  meta?: {
    tone?: string;
    target_slot?: string;
    rationale?: string;
    escalate?: boolean;
  };
  timestamp: string;
}
