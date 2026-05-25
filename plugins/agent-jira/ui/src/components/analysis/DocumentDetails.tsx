import { Database, FileUp, Loader2, RefreshCw, Save } from 'lucide-react';
import { AnalysisResponse } from '../../types';

type DocumentDetailsProps = {
  analysis: AnalysisResponse;
  storing: boolean;
  onStore: () => void;
  onResetSession: () => void;
};

const DocumentDetails = ({ analysis, storing, onStore, onResetSession }: DocumentDetailsProps) => {
  const meta = analysis.metadata || {};
  const docName =
    meta.file_name || meta.filename || meta.name || analysis.kb.label || meta.path || 'Documento';
  const docDisplay = docName.replace(/\.[^./\\]+$/, '');
  const docType = meta.type || meta.mime || meta.mimetype;
  const docSize = meta.size_human || meta.size || meta.bytes;
  const planSummary = analysis.plan?.functional_summary?.trim();
  const planHighlights = (analysis.plan?.key_requirements || []).filter(Boolean);

  const requirementsCount = analysis.plan?.key_requirements?.length ?? 0;
  const storiesCount = analysis.plan?.user_stories?.length ?? 0;
  const risksCount = analysis.plan?.risks?.length ?? 0;
  const openQuestionsCount = analysis.plan?.open_questions?.length ?? 0;

  return (
    <>
      {/* ── Panel header ── */}
      <div className="ws-panel-header">
        <span className="ws-panel-label">Inspector</span>
        <span className={`ws-badge${analysis.kb.from_kb ? ' ws-badge--accent' : ''}`}>
          {analysis.kb.from_kb ? <Database size={9} /> : <FileUp size={9} />}
          {analysis.kb.from_kb ? 'Knowledge Base' : 'Upload'}
        </span>
      </div>

      {/* ── Document identity ── */}
      <div className="ws-inspector-section">
        <div className="ws-inspector-title">Documento</div>
        <div
          style={{
            fontWeight: 700,
            fontSize: 13,
            color: 'var(--text)',
            wordBreak: 'break-all',
            lineHeight: 1.3,
            marginBottom: 10,
          }}
        >
          {docDisplay}
        </div>
        <div
          style={{
            background: 'var(--panel)',
            border: '1px solid var(--border)',
            borderRadius: 8,
            overflow: 'hidden',
          }}
        >
          <div className="ws-prop-row" style={{ padding: '6px 10px' }}>
            <span className="ws-prop-key">Tipo</span>
            <span className="ws-prop-val">{docType || 'Documento'}</span>
          </div>
          <div className="ws-prop-row" style={{ padding: '6px 10px' }}>
            <span className="ws-prop-key">Dimensione</span>
            <span className="ws-prop-val">{docSize || '—'}</span>
          </div>
          <div className="ws-prop-row" style={{ padding: '6px 10px' }}>
            <span className="ws-prop-key">Stato KB</span>
            <span className="ws-prop-val" style={{ fontSize: 11 }}>
              {analysis.kb.status}
            </span>
          </div>
        </div>

        {/* Actions */}
        <div className="ws-action-row">
          {!analysis.kb.from_kb && analysis.kb.can_store && (
            <button
              className="ws-action-btn ws-action-btn--accent"
              onClick={onStore}
              disabled={storing}
            >
              {storing ? <Loader2 size={11} className="ws-spin" /> : <Save size={11} />}
              Salva in KB
            </button>
          )}
          <button className="ws-action-btn" onClick={onResetSession}>
            <RefreshCw size={11} /> Nuova sessione
          </button>
        </div>
      </div>

      {/* ── Metrics ── */}
      <div className="ws-inspector-section">
        <div className="ws-inspector-title">Metriche output</div>
        <div className="ws-metrics-grid">
          <div className="ws-metric-cell">
            <span className="ws-metric-label">Requisiti</span>
            <span className="ws-metric-value">{requirementsCount}</span>
          </div>
          <div className="ws-metric-cell">
            <span className="ws-metric-label">User Stories</span>
            <span className="ws-metric-value">{storiesCount}</span>
          </div>
          <div className="ws-metric-cell">
            <span className="ws-metric-label">Rischi</span>
            <span className="ws-metric-value">{risksCount}</span>
          </div>
          <div className="ws-metric-cell">
            <span className="ws-metric-label">Open Q.</span>
            <span className="ws-metric-value">{openQuestionsCount}</span>
          </div>
        </div>
      </div>

      {/* ── Executive summary ── */}
      <div className="ws-inspector-section">
        <div className="ws-inspector-title">Sintesi esecutiva</div>
        <div className="ws-summary-block">
          {planSummary ? (
            planSummary
          ) : planHighlights.length > 0 ? (
            <ul style={{ margin: 0, paddingLeft: 14 }}>
              {planHighlights.slice(0, 3).map((line, idx) => (
                <li key={idx} style={{ marginBottom: 4 }}>
                  {line}
                </li>
              ))}
            </ul>
          ) : (
            <span style={{ color: 'var(--muted)' }}>Nessuna sintesi disponibile.</span>
          )}
        </div>
      </div>
    </>
  );
};

export default DocumentDetails;
