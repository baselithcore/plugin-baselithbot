export type Role = 'user' | 'assistant';
export type ChatMessageKind = 'message' | 'agent-status';
export type ChatAgentType = 'jira' | 'rag' | 'generic';
export type ChatAgentStepState = 'pending' | 'active' | 'completed';
export type ChatAgentRunState = 'running' | 'completed' | 'blocked';

export interface ChatAction {
  label: string;
  payload: string;
}

export interface ChatAgentStatusStep {
  key: string;
  label: string;
  state: ChatAgentStepState;
}

export interface ChatAgentStatus {
  agent: ChatAgentType;
  title: string;
  detail: string;
  steps: ChatAgentStatusStep[];
  state: ChatAgentRunState;
  summary?: string;
}

export interface ChatMessage {
  role: Role;
  text: string;
  kind?: ChatMessageKind;
  agentStatus?: ChatAgentStatus;
  actions?: ChatAction[];
  duration?: number;
}

export interface ChatSource {
  path?: string;
  url?: string;
  title?: string;
  score?: number;
  score_avg?: number;
  context_ratio?: number;
  origin?: string;
}

export interface ChatResponsePayload {
  answer: string;
  sources: ChatSource[];
  source_metrics?: Record<string, number>;
  project_plan?: ProjectPlanPayload | null;
  jira_issues?: JiraIssue[];
  created_jira_issues?: JiraIssue[];
  jira_manual_required?: boolean;
  suggested_actions?: ChatAction[];
  duration?: number;
}

export interface ChatStreamTokenEvent {
  event_type: 'token';
  text?: string;
  content?: string;
}

export interface ChatStreamStatusEvent {
  event_type: 'status';
  message: string;
  step?: string | null;
  agent?: string | null;
  progress?: number | null;
}

export interface ChatStreamFinalPayloadEvent extends ChatResponsePayload {
  event_type: 'final_payload';
}

export interface ChatStreamErrorEvent {
  event_type: 'error';
  message: string;
  code?: string | null;
}

export type ChatStreamEvent =
  | ChatStreamTokenEvent
  | ChatStreamStatusEvent
  | ChatStreamFinalPayloadEvent
  | ChatStreamErrorEvent;

export interface JiraIssue {
  key?: string | null;
  url?: string | null;
  summary?: string;
  status?: string | null;
  issue_type?: string | null;
  error?: string | null;
}

export interface JiraProject {
  key: string;
  name: string;
}

export interface JiraProjectsResponse {
  projects: JiraProject[];
  default_project_key?: string | null;
  allowed_project_keys?: string[];
}

export interface JiraSyncResponse {
  status: string;
  results: JiraIssue[];
}

export interface ScenarioPayload {
  scenario_id?: string | null;
  title: string;
  given: string[];
  when: string[];
  then: string[];
  priority?: string | null;
}

export interface TestCasePayload {
  title: string;
  objective?: string;
  preconditions: string[];
  test_data: string[];
  steps: string[];
  expected_result: string;
  priority?: string;
  labels?: string[];
  jira_issue_key?: string | null;
}

export interface UserStoryPayload {
  title: string;
  role: string;
  goal: string;
  benefit: string;
  business_value?: string[];
  priority?: string;
  story_points?: number | null;
  labels?: string[];
  scenarios?: ScenarioPayload[];
  test_cases?: TestCasePayload[];
  acceptance?: string[];
  jira_project_key?: string | null;
}

export interface ProjectPlanPayload {
  functional_summary?: string;
  key_requirements?: string[];
  user_stories?: UserStoryPayload[];
  risks?: string[];
  open_questions?: string[];
}

export interface ConsoleConfig {
  chat_enabled: boolean;
  analysis_enabled: boolean;
  jira_enabled: boolean;
  supported_upload_types: string[];
  jira_manual_required: boolean;
  jira_project_key?: string | null;
  auth_required?: boolean;
}

export interface JiraSettings {
  base_url: string;
  email: string;
  api_token_set: boolean;
  project_key: string;
  default_project_key?: string;
  allowed_project_keys?: string[];
  issue_type: string;
  test_case_issue_type?: string;
  source: 'environment' | 'tenant';
}

export interface JiraSettingsResponse {
  status: string;
  settings: JiraSettings;
  configurable: boolean;
}

export interface JiraSettingsPayload {
  base_url: string;
  email: string;
  api_token: string;
  project_key: string;
  default_project_key?: string;
  allowed_project_keys?: string[];
  issue_type: string;
  test_case_issue_type: string;
}

export interface JiraTestResult {
  status: 'ok' | 'error';
  message: string;
  user?: {
    displayName: string;
    emailAddress: string;
    accountId: string;
  };
}

export interface AuthUser {
  id: string;
  email: string;
  display_name: string;
  tenant_id?: string | null;
  role: string;
  is_active?: boolean;
  created_at?: string;
  last_login_at?: string | null;
}

export interface AuthResponse {
  status: string;
  token: string;
  user: AuthUser;
}

export interface KbDocumentEntry {
  path: string;
  label?: string | null;
  stories?: number;
  test_cases?: number;
  jira_search_url?: string | null;
  jira_story_url?: string | null;
  jira_test_url?: string | null;
  uploaded_at?: string | null;
}

export interface KbListResponse {
  documents: KbDocumentEntry[];
  supported_upload_types: string[];
}

export interface AnalysisResponse {
  metadata: Record<string, any>;
  summary: string;
  plan_markdown: string;
  plan: ProjectPlanPayload;
  jira: {
    status: string;
    results: JiraIssue[];
    manual_required: boolean;
    can_manual_sync: boolean;
  };
  kb: {
    from_kb: boolean;
    label?: string | null;
    status: string;
    can_store: boolean;
    upload_path?: string | null;
  };
  duration?: number;
}

export interface GraphNode {
  id: string;
  label: string;
  group: string;
  is_center?: boolean;
  properties?: Record<string, any>;
  [key: string]: any;
}

export interface GraphLink {
  source: string;
  target: string;
  label?: string;
  [key: string]: any;
}

export interface GraphData {
  nodes: GraphNode[];
  links: GraphLink[];
  legend?: Record<string, { color: string; label: string }>;
}
