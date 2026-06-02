// Tipi condivisi col backend FastAPI (`main.py`) e con il generator
// `llm_wiki.agents.rag_agent.RAGAgent.stream` (protocollo graphrag).

export type Role = 'user' | 'assistant';

export interface Source {
  document_id: string;
  title: string;
  score: number;
  relative_path?: string | null;
  page_type?: string | null;
  /** Edizione del documento (stringa come appare). Es: "01/06/2025" */
  edizione?: string | null;
  /** Edizione ISO per ordinamento/filtri. Es: "2025-06-01" */
  edizione_iso?: string | null;
  /** Stato vigenza: vigente | superata | abrogata */
  stato?: 'vigente' | 'superata' | 'abrogata' | null;
  /** Rango normativo (vedi CLAUDE.md gerarchia normativa) */
  rango?:
    | 'regolamento-ue'
    | 'cc-inderogabile'
    | 'cc-derogabile'
    | 'cap'
    | 'regolamento-ivass'
    | 'circolare-ivass'
    | 'condizioni-contrattuali'
    | 'nta'
    | 'accordo-accessorio'
    | 'giurisprudenza'
    | null;
  /** Subtype del contenuto (sentenza, garanzia-assicurativa, ecc.) */
  subtype?: string | null;
  /** Articolo/comma specifico citato dall'LLM (es. "art. 5.1.7 CdA") */
  article_ref?: string | null;
  /** Chunk recuperato via follow-the-link dai rinvii incrociati */
  via_rinvio?: boolean | null;
  /** Snippet verbatim già estratto dal backend (se disponibile) */
  verbatim?: string | null;
  /**
   * Provenance: filename del raw file originale (es. "raw/contract-44.pdf").
   * Solo presente per chunk derivati da source page. Concept/entity page
   * sintetizzate non hanno questo campo.
   */
  source_file?: string | null;
  /**
   * Numero pagine del raw file originale (PDF/DOCX/PPTX). Permette di
   * costruire UI "Pagina N/M" o deep-link `#page=N` al raw file servito
   * dal backend (`GET /api/raw/file/{name}`).
   */
  source_pages_count?: number | null;
}

/**
 * Violazione di citazione segnalata dal backend (post-generation grounding
 * check su [[folder/slug]] della risposta).
 *
 * - `unknown_folder`: folder non in `pack.page_types[*].folder` → hallucination
 * - `slug_not_in_sources`: slug non corrisponde a un document_id recuperato
 * - `malformed`: wikilink senza `/` (`[[noslash]]`)
 */
export interface CitationViolation {
  raw: string;
  folder: string;
  slug: string;
  reason: 'unknown_folder' | 'slug_not_in_sources' | 'malformed';
}

export interface CitationWarning {
  summary: string;
  violations: CitationViolation[];
}

export interface Message {
  id: string;
  role: Role;
  content: string;
  /** emessa dal backend una sola volta, alla fine */
  sources?: Source[];
  /** trace breve degli step (Retriever/RAG/…) */
  trace?: Array<{ agent?: string; step?: string; at?: number }>;
  /** true finché sta arrivando in streaming */
  streaming?: boolean;
  /** error message se l'evento `error` arriva */
  error?: string;
  /** warning citazioni non valide rilevate dal validator backend */
  citationWarning?: CitationWarning;
  /**
   * Query riscritta dal backend per il retrieval (memoria conversazionale).
   * Presente solo quando l'history-aware condenser ha effettivamente
   * riformulato la domanda — UX transparency.
   */
  queryRewrite?: { original: string; rewritten: string };
  createdAt: number;
  /** timestamp invio richiesta (assistant message) */
  startedAt?: number;
  /** timestamp primo token ricevuto */
  firstTokenAt?: number;
  /** timestamp risposta completa */
  completedAt?: number;
}

export interface Conversation {
  id: string;
  title: string;
  messages: Message[];
  createdAt: number;
  updatedAt: number;
  /** titolo fissato dall'utente — se true, auto-derive da deriveTitle è inibito */
  titleLocked?: boolean;
  /** appiccicata in cima, ignora bucket temporale */
  pinned?: boolean;
}

// Stream event (protocollo RAGAgent)
export type StreamEvent =
  | { type: 'agent'; content: string }
  | { type: 'step'; content: string }
  | { type: 'hits'; count: number }
  | { type: 'memories'; items: unknown[] }
  | { type: 'token'; content: string }
  | { type: 'sources'; items: Source[] }
  // emesso solo se backend rileva violazioni alle citazioni della risposta
  // (validator post-generation, env CITATION_VALIDATION_ENABLED).
  | { type: 'citation_warning'; summary: string; violations: CitationViolation[] }
  // primo evento dello stream quando la chat è autenticata: comunica
  // l'id della conversation (auto-creata o riusata) per attach client.
  | { type: 'conversation'; id: string }
  // History-aware retrieval (memoria conversazionale): emesso solo
  // quando il backend ha riscritto la domanda in forma autonoma usando
  // i turni precedenti — UX transparency, l'utente vede cosa il
  // retrieval ha effettivamente cercato.
  | { type: 'query_rewrite'; original: string; rewritten: string }
  // trailer event (Fase 5+): id del messaggio assistant persistito,
  // necessario per il feedback FK.
  | { type: 'message_id'; id: string }
  | { type: 'error'; message: string }
  | { type: 'done' };

// /api/status
export interface ProviderStatus {
  vendor: 'ollama' | 'openai';
  rag_vendor: 'ollama' | 'openai';
  ingest_vendor: 'ollama' | 'openai';
  split: boolean;
  model: string;
  ingest_model: string;
  endpoint: string;
}
export interface EmbedderStatus {
  name: string | null;
  dim: number;
  hybrid: boolean;
}
export interface QdrantStatus {
  mode: 'embedded' | 'server';
  target: string;
  available: boolean;
  collection: string;
  status?: string;
  points?: number;
  hybrid?: boolean;
}
export interface GraphStatus {
  enabled: boolean;
  nodes?: number;
  edges?: number;
}
export interface VaultStatus {
  root: string;
  pages: number;
}
export interface FeatureFlags {
  /** abilita UI voto 👍/👎 + invio `POST /api/feedback` */
  feedback_enabled: boolean;
}
export interface Status {
  provider: ProviderStatus;
  embedder: EmbedderStatus;
  qdrant: QdrantStatus;
  graph: GraphStatus;
  vault: VaultStatus;
  features?: FeatureFlags;
}

// /api/wiki/pages
export interface WikiPageMeta {
  document_id: string;
  title: string;
  type: string;
  category: string;
  tags: string[];
  wikilinks_count: number;
}

// /api/editions
export interface EditionSource {
  document_id: string;
  title: string;
  source_type: string | null;
}

export interface EditionMeta {
  id: string;
  label: string;
  edizione: string;
  edizione_iso: string;
  stato: 'vigente' | 'superata' | 'abrogata';
  note: string;
  codice_prodotto: string | null;
  modello: string | null;
  sources: EditionSource[];
}

// /api/ingest/raw (upload + job)
export type IngestJobStatus = 'queued' | 'running' | 'done' | 'error';

export interface IngestJob {
  id: string;
  filename: string;
  status: IngestJobStatus;
  options: {
    overwrite?: boolean;
    reindex?: boolean;
    dry_run?: boolean;
    only_source_page?: boolean;
  };
  created_at: number;
  started_at: number | null;
  finished_at: number | null;
  backend: string | null;
  pages_written: number;
  pages_needs_review: number;
  pages_conflict: number;
  pages_error: number;
  errors: string[];
  summary: string;
}

export type IngestPagePhase =
  | 'extract'
  | 'classify'
  | 'plan'
  | 'generate'
  | 'lint'
  | 'write'
  | 'reindex'
  | 'error'
  | 'warn'
  | 'info';

export type IngestPageStatus = 'written' | 'conflict' | 'dry-run' | 'needs-review' | 'error';

export type IngestStreamEvent =
  | {
      type: 'status';
      status: IngestJobStatus;
      message: string;
      t: number;
    }
  | {
      type: 'log';
      phase: IngestPagePhase;
      level: 'info' | 'warning' | 'error' | 'debug' | 'critical';
      logger: string;
      message: string;
      t: number;
    }
  | {
      type: 'page';
      path: string;
      status: IngestPageStatus;
      iterations: number;
      bytes: number;
      message: string;
      t: number;
    }
  | ({ type: 'final' } & IngestJob);

export interface RawFileMeta {
  name: string;
  size: number;
  modified: number;
  /**
   * True when the file already has a corresponding source page on disk
   * (incl. `.needs-review.md` / `.new.md` outputs). Files with
   * `processed=true` are NOT "waiting" — they've been ingested, just
   * possibly with a critic-rejected outcome.
   */
  processed?: boolean;
}
