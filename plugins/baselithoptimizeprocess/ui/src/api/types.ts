// Domain types mirroring the BOP backend Pydantic models.

export type KpiDirection = 'minimize' | 'maximize';
export type NodeKind = 'start' | 'task' | 'decision' | 'parallel' | 'end';
export type Severity = 'low' | 'medium' | 'high' | 'critical';
export type ProposalStatus = 'proposed' | 'approved' | 'rejected' | 'applied';

export interface KpiDefinition {
  id: string;
  name: string;
  unit: string;
  direction: KpiDirection;
  target: number | null;
  description: string;
}

export interface NodeCost {
  labor_cost_per_hour: number;
  avg_handling_seconds: number;
  rework_rate: number;
  fixed_cost: number;
}

export interface ProcessNode {
  id: string;
  name: string;
  kind: NodeKind;
  role: string;
  resource_id?: string | null;
  cost?: NodeCost | null;
  metadata: Record<string, string>;
}

export interface Resource {
  id: string;
  name: string;
  role: string;
  cost_per_hour: number;
  currency: string;
  capacity_hours_per_week: number | null;
  skills: string[];
  active: boolean;
  metadata: Record<string, string>;
  created_at: string;
  updated_at: string;
}

export interface ProcessEdge {
  source: string;
  target: string;
  condition: string;
}

export interface ProcessGraph {
  id: string;
  name: string;
  description: string;
  nodes: ProcessNode[];
  edges: ProcessEdge[];
  kpis: KpiDefinition[];
  currency: string;
  annual_case_volume: number | null;
  created_at: string;
  updated_at: string;
}

export interface MoneyImpact {
  amount: number;
  currency: string;
  period: string;
  basis: string;
}

export interface CostReport {
  process_id: string;
  currency: string;
  per_case_cost: number;
  annual_cost: number | null;
  node_costs: Record<string, number>;
  costed_nodes: number;
  total_nodes: number;
}

export interface SimulationResult {
  process_id: string;
  cycle_time_seconds: number;
  cost_per_case: number;
  currency: string;
  annual_cost: number | null;
  bottleneck_node: string | null;
  critical_path: string[];
  assumptions: string;
}

export interface SimulationComparison {
  baseline: SimulationResult;
  variant: SimulationResult;
  cycle_time_delta_seconds: number;
  cost_per_case_delta: number;
  annual_cost_delta: number | null;
  cycle_time_pct: number;
  cost_pct: number;
}

export interface Anomaly {
  process_id: string;
  kpi_id: string;
  value: number;
  expected: number;
  z_score: number;
  at: string;
}

export interface BreachForecast {
  process_id: string;
  kpi_id: string;
  current: number;
  target: number | null;
  slope_per_sample: number;
  projected_value: number;
  will_breach: boolean;
  samples_to_breach: number | null;
  horizon: number;
}

export type ChangeStatus = 'active' | 'monitoring' | 'kept' | 'rolled_back';

export interface AppliedChange {
  id: string;
  process_id: string;
  proposal_id: string;
  from_version: number | null;
  to_version: number;
  status: ChangeStatus;
  guard: { kpi_id: string; max_regression_pct: number } | null;
  baseline_value: number | null;
  applied_by: string;
  applied_at: string;
  resolved_at: string | null;
  detail: string;
}

export interface KpiSnapshot {
  process_id: string;
  kpi_id: string;
  value: number;
  target: number | null;
  direction: KpiDirection;
  breaching: boolean;
  sample_count: number;
  timestamp: string;
}

export interface Bottleneck {
  process_id: string;
  kpi_id: string;
  node_id: string | null;
  severity: Severity;
  observed: number;
  target: number | null;
  detail: string;
  detected_at: string;
}

export interface OptimizationProposal {
  id: string;
  process_id: string;
  title: string;
  rationale: string;
  target_nodes: string[];
  addresses_kpis: string[];
  expected_impact: string;
  confidence: number;
  estimated_savings?: MoneyImpact | null;
  status: ProposalStatus;
  created_at: string;
  decided_at: string | null;
}

export interface MetricsEvent {
  type: 'metrics';
  process_id: string;
  snapshots: KpiSnapshot[];
  bottlenecks: Bottleneck[];
}

// -- DataOps: mining, conformance, automation -----------------------------

export interface EventRecord {
  case_id: string;
  activity: string;
  timestamp: string;
  resource?: string;
}

export interface ActivityStat {
  activity: string;
  occurrences: number;
  avg_wait_seconds: number;
  rework_count: number;
}

export interface Variant {
  sequence: string[];
  count: number;
  avg_duration_seconds: number;
}

export interface MiningResult {
  process_id: string;
  case_count: number;
  activity_stats: ActivityStat[];
  variants: Variant[];
  avg_case_duration_seconds: number;
  rework_cases: number;
  rework_rate: number;
  self_loops: string[];
  concurrent_activities: string[][];
}

export interface TransitionDeviation {
  source: string;
  target: string;
  count: number;
}

export interface ConformanceReport {
  process_id: string;
  fitness: number;
  alignment_fitness: number;
  avg_case_fitness: number;
  conforming_cases: number;
  deviating_cases: number;
  undesired_transitions: TransitionDeviation[];
  unseen_activities: string[];
  deviation_cost: number;
  currency: string;
}

export type TriggerType = 'kpi_breach' | 'bottleneck_severity' | 'predicted_breach';
export type ActionType = 'alert' | 'recommend_optimization' | 'webhook';

export interface RuleTrigger {
  type: TriggerType;
  kpi_id: string;
  min_severity: string;
}

export interface RuleAction {
  type: ActionType;
  message: string;
  webhook_url: string;
}

export interface AutomationRule {
  id: string;
  process_id: string;
  name: string;
  trigger: RuleTrigger;
  action: RuleAction;
  enabled: boolean;
  created_at: string;
}

export interface RuleFiring {
  rule_id: string;
  process_id: string;
  rule_name: string;
  action_type: ActionType;
  detail: string;
  fired_at: string;
}

export interface AutomationEvent {
  type: 'automation';
  process_id: string;
  firings: RuleFiring[];
}

export interface ProcessVersion {
  process_id: string;
  version: number;
  content_hash: string;
  graph: ProcessGraph;
  summary: string;
  actor: string;
  created_at: string;
}

export interface AuditEvent {
  id: string;
  tenant_id: string;
  actor: string;
  action: string;
  target_type: string;
  target_id: string;
  process_id: string;
  detail: string;
  created_at: string;
}

// -- Insights: variants, performance/SLA, root cause ----------------------

export interface Distribution {
  count: number;
  mean: number;
  p50: number;
  p90: number;
  p95: number;
  p99: number;
  min: number;
  max: number;
}

export interface VariantDetail {
  id: string;
  sequence: string[];
  count: number;
  share: number;
  duration: Distribution;
  conforms: boolean;
  deviation_count: number;
  cost_per_case: number;
  is_happy_path: boolean;
}

export interface VariantReport {
  process_id: string;
  case_count: number;
  variant_count: number;
  happy_path_id: string | null;
  conforming_cases: number;
  deviating_cases: number;
  rare_variant_count: number;
  currency: string;
  variants: VariantDetail[];
}

export type SlaScope = 'case' | 'activity';

export interface SlaDefinition {
  id: string;
  process_id: string;
  name: string;
  scope: SlaScope;
  activity: string;
  threshold_seconds: number;
  created_at: string;
}

export interface SlaResult {
  sla_id: string;
  name: string;
  scope: SlaScope;
  activity: string;
  threshold_seconds: number;
  observations: number;
  breaches: number;
  breach_rate: number;
  worst_value: number;
  p90_value: number;
}

export interface ActivityPerformance {
  activity: string;
  occurrences: number;
  wait: Distribution;
}

export interface PerformanceReport {
  process_id: string;
  case_count: number;
  cycle_time: Distribution;
  activities: ActivityPerformance[];
  slas: SlaResult[];
}

export interface VariantDiff {
  a_id: string;
  b_id: string;
  a_sequence: string[];
  b_sequence: string[];
  added_steps: string[];
  removed_steps: string[];
  shared_steps: string[];
  count_delta: number;
  cycle_time_p50_delta: number;
  cycle_time_p90_delta: number;
  cost_delta: number;
  currency: string;
}

// Case-level segmentation passed to variant/performance/root-cause queries.
export interface EventFilter {
  start_after?: string;
  end_before?: string;
  activity?: string;
  resource?: string;
  variant_id?: string;
  min_duration_seconds?: number;
  max_duration_seconds?: number;
}

// -- Predictive monitoring ------------------------------------------------

export interface NextActivity {
  activity: string;
  probability: number;
}

export interface StatePrediction {
  activity: string;
  observations: number;
  remaining: Distribution;
  next_activities: NextActivity[];
  is_terminal: boolean;
}

export interface PredictorModel {
  process_id: string;
  case_count: number;
  states: StatePrediction[];
}

export interface SlaPrediction {
  sla_id: string;
  name: string;
  threshold_seconds: number;
  projected_seconds: number;
  violation_probability: number;
  will_breach: boolean;
}

export interface CasePrediction {
  process_id: string;
  case_id: string;
  current_activity: string;
  elapsed_seconds: number;
  completed: boolean;
  predicted_remaining_seconds: number;
  predicted_remaining_p90_seconds: number;
  predicted_total_seconds: number;
  next_activities: NextActivity[];
  confidence: number;
  slas: SlaPrediction[];
}

export type FactorDimension = 'resource' | 'activity' | 'variant' | 'pattern';

export interface RootCauseFactor {
  dimension: FactorDimension;
  factor: string;
  cases_with_factor: number;
  bad_with_factor: number;
  factor_breach_rate: number;
  baseline_rate: number;
  lift: number;
  impact_score: number;
}

export interface RootCauseReport {
  process_id: string;
  outcome: string;
  threshold_seconds: number;
  total_cases: number;
  bad_cases: number;
  baseline_rate: number;
  factors: RootCauseFactor[];
}
