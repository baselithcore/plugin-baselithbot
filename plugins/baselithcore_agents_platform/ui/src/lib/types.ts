// Mirror of the backend domain model (plugins/.../types.py). Kept hand-written
// and small so the UI has no codegen step.

export type ModelProvider = 'anthropic' | 'openai' | 'ollama';

export type AgentCapability = 'generate' | 'fix' | 'test' | 'refactor' | 'explain' | 'operate';

export type RunStatus = 'pending' | 'running' | 'succeeded' | 'failed' | 'rejected';

export interface BlueprintScope {
  capabilities: AgentCapability[];
  doc_namespaces: string[];
  allowed_tools: string[];
  max_iterations: number;
  language: string;
  allow_execution: boolean;
}

export interface ScheduleSpec {
  id: string;
  blueprint_id: string;
  capability: AgentCapability;
  task: string;
  interval_seconds: number;
  enabled: boolean;
  runs: number;
  last_run_at: string | null;
  last_status: RunStatus | null;
  last_error: string | null;
  created_at: string;
}

export interface AgentBlueprint {
  id: string;
  name: string;
  description: string;
  system_directive: string;
  provider: ModelProvider;
  model: string | null;
  scope: BlueprintScope;
  tags: string[];
  source_prompt: string;
  created_at: string;
}

export interface DocCitation {
  namespace: string;
  snippet: string;
  score: number;
}

export interface AgentRunResult {
  run_id: string;
  blueprint_id: string;
  capability: AgentCapability;
  status: RunStatus;
  output: string;
  explanation: string;
  iterations: number;
  error: string | null;
  citations: DocCitation[];
  created_at: string;
}

export interface ModelInfo {
  provider: ModelProvider;
  default_model: string;
  requires_api_key: boolean;
  local: boolean;
}
