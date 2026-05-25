export type Severity = "FAIL" | "WARN" | "PASS" | "INFO";

export interface PolicyRef {
  id: string;
  policy_id: string;
  version: string;
  title: string;
  excerpt: string;
}

export interface Citation {
  chunk_id: string;
  page: number;
  line_start: number;
  line_end: number;
  bbox: [number, number, number, number];
  text: string;
  match_start?: number | null;
  match_end?: number | null;
  snippet?: string | null;
}

export interface ReasoningStep {
  step: number;
  agent: string;
  action?: string;
  input?: Record<string, unknown>;
  output?: Record<string, unknown>;
  thought?: string;
}

export interface Finding {
  id: string;
  severity: Severity;
  rule_id: string;
  policy_ref: PolicyRef;
  evidence: Citation;
  explanation: string;
  suggestion?: string;
  confidence: number;
  reasoning: ReasoningStep[];
}

export interface Report {
  report_id: string;
  doc_id: string;
  score: number;
  by_severity: Record<Severity, number>;
  findings: Finding[];
  signature: string;
  policies_applied?: string[];
  chunks_evaluated?: number;
  engine_errors?: string[];
}

export interface PolicyRow {
  id: string;
  version: string;
  title: string;
  scope: "global_default" | "eu" | "world" | "custom";
  lang: string;
  active: boolean;
  rule_count: number;
  system?: boolean;
}

export interface CoverageGap {
  label: string;
  excerpt: string;
  severity_hint: "fail" | "warn" | "info";
}

export interface CoverageReport {
  extracted_count: number;
  detected_count: number;
  coverage_ratio: number;
  gaps: CoverageGap[];
}

export interface IngestPolicyRow extends PolicyRow {
  coverage?: CoverageReport | null;
}

export type RuleType =
  | "presence"
  | "absence"
  | "format"
  | "numeric_limit"
  | "semantic";
export type RuleSeverity = "fail" | "warn" | "info";

export interface RuleRow {
  id: string;
  policy_id: string;
  policy_version: string;
  rule_type: RuleType;
  severity: RuleSeverity;
  excerpt: string;
  matcher?: string | null;
}

export interface RulePayload {
  id?: string;
  rule_type: RuleType;
  severity: RuleSeverity;
  excerpt: string;
  matcher?: string | null;
}

export interface PolicyCreatePayload {
  id: string;
  version: string;
  title: string;
  scope: PolicyRow["scope"];
  lang: string;
  active: boolean;
  rules: RulePayload[];
}

export interface PolicyPatchPayload {
  title?: string;
  scope?: PolicyRow["scope"];
  lang?: string;
}

export interface LatestReportSummary {
  report_id: string;
  score: number;
  signed_at: string;
}

export type DocType =
  | "contract"
  | "policy"
  | "procedure"
  | "dpia"
  | "audit_report"
  | "manual"
  | "technical_spec"
  | "regulatory_text"
  | "other";

export interface DocumentRow {
  id: string;
  filename: string;
  mime_type: string;
  sha256: string;
  size_bytes: number;
  pages: number | null;
  lang: string | null;
  status: string;
  doc_type?: DocType | null;
  doc_type_confidence?: number | null;
  uploaded_at: string;
  latest_report?: LatestReportSummary | null;
}

export interface DocumentReportRow {
  report_id: string;
  doc_id: string;
  score: number;
  engine_version: string;
  model_id: string;
  signed_at: string;
}

export interface ChunkRow {
  id: string;
  page: number | null;
  line_start: number | null;
  line_end: number | null;
  bbox: string | null;
  text: string;
}

export interface ListDocumentsParams {
  limit?: number;
  offset?: number;
  q?: string;
  status?: string[];
}

export interface ListDocumentsResult {
  rows: DocumentRow[];
  total: number;
}

export interface QueueMetric {
  value: number;
  trend_7d?: number;
  trend_30d?: number;
}
export interface WorkspaceQueue {
  in_review: QueueMetric;
  pending_approval: QueueMetric;
  compliant: QueueMetric;
}

export interface ActivePolicy {
  id: string;
  version: string;
  title: string;
  scope: PolicyRow["scope"];
  lang: string;
}

export interface RecentActivity {
  report_id: string;
  doc_id: string;
  filename: string;
  score: number;
  signed_at: string;
}

export type DecisionKind = "accepted" | "rejected" | "muted";

export interface Decision {
  decision: DecisionKind | null;
  note?: string | null;
  user_id?: string;
  decided_at?: string;
}

export interface ReportSummary {
  report_id: string;
  verdict: "compliant" | "attention" | "critical";
  headline: string;
  assessment: string;
  top_risks: string[];
  next_steps: string[];
  score: number;
  fallback?: boolean;
}

export interface HealthInfo {
  status: string;
  version: string;
  llm_provider?: string;
  llm_model?: string;
  llm_base_url?: string;
}

export interface CacheMetrics {
  embedding?: { hits: number; misses: number; ratio: number };
  verdict?: { hits: number; misses: number; ratio: number };
  [k: string]: unknown;
}
