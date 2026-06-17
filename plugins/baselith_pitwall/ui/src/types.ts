export interface Status {
  version: string;
  running: boolean;
  cars_tracked: number;
  frames_ingested: number;
  recommendations_emitted: number;
  queue_depth: number;
  swarm_agents: number;
  llm_enabled: boolean;
  semantic_enabled: boolean;
}

export interface Stint {
  car_id: string;
  lap: number;
  total_laps: number;
  position: number;
  compound: string;
  tyre_age_laps: number;
  tyre_wear: number;
  deg_rate_per_lap: number;
  fuel_kg: number;
  engine_temp_c: number;
  gap_ahead_s: number | null;
  gap_behind_s: number | null;
}

export interface Scenario {
  actions: string[];
  expected_position: number;
  expected_race_time_s: number;
  reward: number;
  probability: number;
}

export interface FIAVerdict {
  compliant: boolean;
  violations: string[];
  notes: string[];
}

export interface BattleForecast {
  rival_id: string;
  laps_to_striking_distance: number | null;
  closing_rate_s_per_lap: number;
  undercut_delta_s: number;
  verdict: string;
}

export interface StrategyOutcome {
  samples: number;
  p_win: number;
  p_podium: number;
  expected_finish: number;
  best_strategy: string;
  neutralisation_rate: number;
}

export interface Recommendation {
  id: string;
  car_id: string;
  lap: number;
  kind: string;
  summary: string;
  rationale: string;
  confidence: number;
  fia_verdict: FIAVerdict;
  scenario: Scenario | null;
  battle: BattleForecast | null;
  outcome: StrategyOutcome | null;
  race_control: string | null;
  pheromone_signals: Record<string, number>;
  historical_refs: string[];
  created_at: string;
}

export type RaceControlStatus = 'green' | 'yellow' | 'vsc' | 'safety_car';

export interface Provenance {
  sources: string[];
  agreement: number;
  contributions: Record<string, number>;
}

export interface FusedIndicator {
  key: string;
  label: string;
  value: number;
  severity: 'low' | 'medium' | 'high' | 'critical';
  confidence: number;
  rationale: string;
  provenance: Provenance;
}

export interface IndicatorSet {
  car_id: string;
  lap: number;
  indicators: FusedIndicator[];
  generated_at: string;
}

export type SessionStatus = 'configuring' | 'live' | 'paused' | 'finished' | 'archived';

export type SourceKind = 'simulated' | 'file_replay' | 'websocket' | 'udp' | 'manual';

export interface RaceSession {
  id: string;
  tenant_id: string;
  name: string;
  circuit: string;
  season: string;
  total_laps: number;
  source_kind: SourceKind;
  status: SessionStatus;
  created_at: string;
  started_at: string | null;
  ended_at: string | null;
}

export interface AuditRecord {
  id: string;
  session_id: string;
  actor: string;
  action: string;
  car_id: string | null;
  detail: Record<string, unknown>;
  created_at: string;
}

export type AckStatus = 'accepted' | 'rejected' | 'deferred';

export interface RecommendationAck {
  id: string;
  recommendation_id: string;
  car_id: string;
  status: AckStatus;
  actor: string;
  note: string;
  created_at: string;
}
