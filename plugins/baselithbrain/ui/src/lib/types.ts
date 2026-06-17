// Wire types — mirror the backend Pydantic DTOs (backend/models.py).

export interface NoteMeta {
  id: string;
  title: string;
  tags: string[];
  created: string | null;
  updated: string | null;
  path: string;
  parent: string | null;
  order: number | null;
  workspace: string;
}

export interface Workspace {
  id: string;
  name: string;
  color: string | null;
  icon: string | null;
  description: string;
  order: number | null;
  created: string | null;
  updated: string | null;
}

export interface WorkspaceInfo extends Workspace {
  note_count: number;
}

export interface TreeNode {
  id: string;
  title: string;
  children: TreeNode[];
}

export interface Note extends NoteMeta {
  body: string;
  links: string[];
  backlinks: string[];
}

export interface SearchHit {
  id: string;
  title: string;
  score: number;
  snippet: string;
  kind: 'keyword' | 'semantic' | 'hybrid';
}

export interface GraphNode {
  id: string;
  label: string;
  kind: 'note' | 'tag' | 'moc';
  degree: number;
}

export interface GraphEdge {
  source: string;
  target: string;
  kind: 'explicit' | 'derived' | 'tag';
}

export interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface LinkSuggestion {
  id: string;
  title: string;
  score: number;
  reason: 'semantic' | 'unlinked-mention';
}

export interface MocCandidate {
  tag: string;
  size: number;
  members: string[];
}

export interface AiStatus {
  configured: boolean;
  provider: string | null;
  model: string | null;
}

export interface ChatSource {
  n: number;
  id: string;
  title: string;
  snippet?: string;
}

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  sources: ChatSource[];
  ts: string | null;
}

export interface ConversationMeta {
  id: string;
  title: string;
  workspace: string;
  created: string | null;
  updated: string | null;
  message_count: number;
}

export interface Conversation extends ConversationMeta {
  messages: ChatMessage[];
  summary: string;
  summarized_count: number;
}

/** How faithful an answer is to its cited notes (LLM-as-judge, 0–1). */
export interface Groundedness {
  score: number;
  level: string;
  feedback: string;
}

export type ChatEvent =
  | { type: 'meta'; conversation_id: string; title: string }
  | { type: 'token'; text: string }
  | { type: 'sources'; sources: ChatSource[] }
  | { type: 'groundedness'; score: number; level: string; feedback: string }
  | { type: 'error'; message: string };

/** One Thought/Action/Observation entry from a deep-research run. */
export interface ResearchTraceStep {
  type: string;
  content: string;
  tool: string | null;
}

/** Result of a deep-research (ReAct) run over the vault. */
export interface ResearchResult {
  answer: string;
  sources: { id: string; title: string }[];
  trace: ResearchTraceStep[];
  iterations: number;
  hit_limit: boolean;
}

export interface TransformResult {
  action: string;
  result?: string;
  tags?: string[];
  suggestions?: string[];
  error?: string;
}
