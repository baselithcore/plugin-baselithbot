-- =====================================================================
-- DocCheck DB Schema (SQLCipher)
-- Version: 0.1.0
-- =====================================================================
-- PRAGMA cipher_page_size = 4096;
-- PRAGMA kdf_iter = 256000;
-- PRAGMA cipher_hmac_algorithm = HMAC_SHA512;
-- PRAGMA cipher_kdf_algorithm = PBKDF2_HMAC_SHA512;
-- =====================================================================

PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;

-- =====================================================================
-- CORE: Identity & RBAC
-- =====================================================================

CREATE TABLE users (
  id            TEXT PRIMARY KEY,
  email         TEXT UNIQUE NOT NULL,
  display_name  TEXT NOT NULL,
  pw_hash       TEXT,                       -- argon2id; NULL se OIDC
  oidc_sub      TEXT UNIQUE,
  created_at    TEXT NOT NULL DEFAULT (datetime('now')),
  disabled_at   TEXT
);

CREATE TABLE roles (
  id    TEXT PRIMARY KEY,                   -- 'admin'|'compliance_officer'|'dpo'|'reader'
  label TEXT NOT NULL
);

CREATE TABLE user_roles (
  user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  role_id TEXT NOT NULL REFERENCES roles(id),
  PRIMARY KEY (user_id, role_id)
);

CREATE TABLE permissions (
  role_id  TEXT NOT NULL REFERENCES roles(id),
  resource TEXT NOT NULL,                   -- 'document'|'policy'|'report'|'audit'
  action   TEXT NOT NULL,                   -- 'read'|'write'|'delete'|'export'|'sign'
  PRIMARY KEY (role_id, resource, action)
);

INSERT INTO roles (id, label) VALUES
  ('admin', 'Administrator'),
  ('compliance_officer', 'Compliance Officer'),
  ('dpo', 'Data Protection Officer'),
  ('reader', 'Reader');

-- Default permissions seed
INSERT INTO permissions (role_id, resource, action) VALUES
  ('admin', 'document', 'read'), ('admin', 'document', 'write'), ('admin', 'document', 'delete'),
  ('admin', 'policy', 'read'), ('admin', 'policy', 'write'), ('admin', 'policy', 'delete'),
  ('admin', 'report', 'read'), ('admin', 'report', 'export'), ('admin', 'report', 'sign'),
  ('admin', 'audit', 'read'),
  ('compliance_officer', 'document', 'read'), ('compliance_officer', 'document', 'write'),
  ('compliance_officer', 'policy', 'read'), ('compliance_officer', 'policy', 'write'),
  ('compliance_officer', 'report', 'read'), ('compliance_officer', 'report', 'export'), ('compliance_officer', 'report', 'sign'),
  ('dpo', 'document', 'read'),
  ('dpo', 'policy', 'read'),
  ('dpo', 'report', 'read'),
  ('dpo', 'audit', 'read'),
  ('reader', 'document', 'read'),
  ('reader', 'policy', 'read'),
  ('reader', 'report', 'read');

-- =====================================================================
-- DOCUMENTS
-- =====================================================================

CREATE TABLE documents (
  id          TEXT PRIMARY KEY,
  owner_id    TEXT NOT NULL REFERENCES users(id),
  filename    TEXT NOT NULL,
  mime_type   TEXT NOT NULL,
  sha256      TEXT NOT NULL,
  size_bytes  INTEGER NOT NULL,
  pages       INTEGER,
  lang        TEXT,                         -- ISO 639-1
  storage_uri TEXT NOT NULL,                -- file://encrypted-vol/...
  uploaded_at TEXT NOT NULL DEFAULT (datetime('now')),
  purge_at    TEXT,                         -- TTL retention
  status      TEXT NOT NULL DEFAULT 'uploaded'
                CHECK (status IN ('uploaded','parsed','indexed','failed','purged'))
);
CREATE INDEX idx_doc_owner ON documents(owner_id);
CREATE INDEX idx_doc_sha   ON documents(sha256);
CREATE INDEX idx_doc_status ON documents(status);

CREATE TABLE document_chunks (
  id          TEXT PRIMARY KEY,
  doc_id      TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
  ord         INTEGER NOT NULL,
  page        INTEGER,
  line_start  INTEGER,
  line_end    INTEGER,
  bbox        TEXT,                         -- JSON [x0,y0,x1,y1]
  text        TEXT NOT NULL,
  token_count INTEGER,
  embed_ref   TEXT                          -- chroma point id
);
CREATE INDEX idx_chunk_doc ON document_chunks(doc_id, ord);

CREATE TABLE document_structure (
  id          TEXT PRIMARY KEY,
  doc_id      TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
  parent_id   TEXT REFERENCES document_structure(id),
  node_type   TEXT NOT NULL                 -- 'title'|'section'|'article'|'clause'|'table'|'signature'
                CHECK (node_type IN ('title','section','article','clause','table','signature')),
  label       TEXT NOT NULL,
  page        INTEGER,
  line_start  INTEGER,
  line_end    INTEGER,
  chunk_ids   TEXT                          -- JSON array
);
CREATE INDEX idx_struct_doc ON document_structure(doc_id);

-- =====================================================================
-- POLICIES
-- =====================================================================

CREATE TABLE policies (
  id          TEXT NOT NULL,                -- 'IT_GDPR_2026'
  version     TEXT NOT NULL,                -- semver
  title       TEXT NOT NULL,
  scope       TEXT NOT NULL                 -- 'global_default'|'eu'|'world'|'custom'
                CHECK (scope IN ('global_default','eu','world','custom')),
  lang        TEXT NOT NULL,
  source_uri  TEXT,
  active      INTEGER NOT NULL DEFAULT 1,
  created_by  TEXT REFERENCES users(id),
  created_at  TEXT NOT NULL DEFAULT (datetime('now')),
  PRIMARY KEY (id, version)
);

CREATE TABLE policy_rules (
  id              TEXT PRIMARY KEY,         -- 'GDPR-Art-13'
  policy_id       TEXT NOT NULL,
  policy_version  TEXT NOT NULL,
  rule_type       TEXT NOT NULL             -- 'presence'|'absence'|'format'|'numeric_limit'|'semantic'
                    CHECK (rule_type IN ('presence','absence','format','numeric_limit','semantic')),
  severity        TEXT NOT NULL
                    CHECK (severity IN ('fail','warn','info')),
  excerpt         TEXT NOT NULL,            -- verbatim policy text per citazione
  matcher         TEXT,                     -- JSON: regex/numeric/semantic_query
  embed_ref       TEXT,
  FOREIGN KEY (policy_id, policy_version) REFERENCES policies(id, version)
);
CREATE INDEX idx_rule_policy ON policy_rules(policy_id, policy_version);

-- =====================================================================
-- REPORTS & FINDINGS
-- =====================================================================

CREATE TABLE reports (
  id               TEXT PRIMARY KEY,
  doc_id           TEXT NOT NULL REFERENCES documents(id),
  user_id          TEXT NOT NULL REFERENCES users(id),
  engine_version   TEXT NOT NULL,
  model_id         TEXT NOT NULL,
  embedding_model  TEXT NOT NULL,
  score            INTEGER NOT NULL,
  policies_applied TEXT NOT NULL,           -- JSON array of "id@version"
  payload          TEXT NOT NULL,           -- JSON full report
  signature        TEXT NOT NULL,           -- ed25519
  signed_at        TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX idx_report_doc  ON reports(doc_id);
CREATE INDEX idx_report_user ON reports(user_id);

CREATE TABLE findings (
  id           TEXT PRIMARY KEY,
  report_id    TEXT NOT NULL REFERENCES reports(id) ON DELETE CASCADE,
  rule_id      TEXT NOT NULL REFERENCES policy_rules(id),
  chunk_id     TEXT NOT NULL REFERENCES document_chunks(id),
  severity     TEXT NOT NULL
                 CHECK (severity IN ('FAIL','WARN','PASS','INFO')),
  confidence   REAL NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
  explanation  TEXT NOT NULL,
  suggestion   TEXT,
  reasoning    TEXT NOT NULL                -- JSON trace agent steps
);
CREATE INDEX idx_finding_report ON findings(report_id);
CREATE INDEX idx_finding_rule   ON findings(rule_id);

-- =====================================================================
-- AUDIT (append-only, hash-chained)
-- =====================================================================

CREATE TABLE audit_log (
  seq          INTEGER PRIMARY KEY AUTOINCREMENT,
  ts           TEXT NOT NULL DEFAULT (datetime('now')),
  user_id      TEXT REFERENCES users(id),
  action       TEXT NOT NULL,               -- 'login'|'upload'|'analyze'|'view_finding'|'export_report'|'policy_create'|'policy_activate'
  resource     TEXT,                        -- e.g. 'document:uuid' or 'policy:GDPR-Art-13'
  payload_hash TEXT NOT NULL,               -- sha256 of canonical payload JSON
  payload_uri  TEXT,                        -- optional pointer to encrypted blob
  prev_hash    TEXT NOT NULL,               -- chain link
  entry_hash   TEXT NOT NULL,               -- sha256(prev_hash || canonical(this row))
  signature    TEXT NOT NULL                -- ed25519 sign(entry_hash)
);
CREATE INDEX idx_audit_ts     ON audit_log(ts);
CREATE INDEX idx_audit_user   ON audit_log(user_id);
CREATE INDEX idx_audit_action ON audit_log(action);

-- Immutability triggers
CREATE TRIGGER audit_no_update
BEFORE UPDATE ON audit_log
BEGIN
  SELECT RAISE(FAIL, 'audit_log is immutable');
END;

CREATE TRIGGER audit_no_delete
BEFORE DELETE ON audit_log
BEGIN
  SELECT RAISE(FAIL, 'audit_log is immutable');
END;

-- =====================================================================
-- CACHE
-- =====================================================================

CREATE TABLE verdict_cache (
  cache_key    TEXT PRIMARY KEY,            -- sha256(chunk_hash || rule_id || rule_version || model_id)
  finding_json TEXT NOT NULL,
  created_at   TEXT NOT NULL DEFAULT (datetime('now')),
  hit_count    INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX idx_verdict_created ON verdict_cache(created_at);

CREATE TABLE embedding_cache (
  text_hash  TEXT PRIMARY KEY,
  model_id   TEXT NOT NULL,
  vector_uri TEXT NOT NULL,                 -- chroma id
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX idx_embed_model ON embedding_cache(model_id);

-- =====================================================================
-- SETTINGS (singleton key-value)
-- =====================================================================

CREATE TABLE settings (
  key         TEXT PRIMARY KEY,
  value       TEXT NOT NULL,
  updated_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

INSERT INTO settings (key, value) VALUES
  ('engine.version', '0.1.0'),
  ('model.primary', 'llama-3.3-70b-instruct-q4km'),
  ('model.fallback', 'llama-3.1-8b-instruct'),
  ('embedding.model', 'bge-m3'),
  ('ocr.engine', 'paddleocr'),
  ('audit.signing_pubkey', ''),
  ('retention.default_days', '365');
