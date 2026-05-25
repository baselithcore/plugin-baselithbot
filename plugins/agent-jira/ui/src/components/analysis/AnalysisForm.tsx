import { useRef, ChangeEvent, useEffect, useState } from 'react';
import {
  CheckCircle,
  Database,
  FileText,
  Loader2,
  LoaderCircle,
  RefreshCw,
  UploadCloud,
  Wand2,
  X,
} from 'lucide-react';
import { KbDocumentEntry } from '../../types';
import FloatingToast, { ToastPayload } from './FloatingToast';

type AnalysisFormProps = {
  prompt: string;
  onPromptChange: (value: string) => void;
  selectedKb: string;
  onKbChange: (value: string) => void;
  file: File | null;
  kbDocuments: KbDocumentEntry[];
  onFileChange: (event: ChangeEvent<HTMLInputElement>) => void;
  onAnalyze: () => void;
  loading: boolean;
  disableAnalyze: boolean;
  error?: string | null;
  toast: ToastPayload | null;
  onResetSession: () => void;
  hasAnalysis: boolean;
  duration?: number;
  analysisStartTime?: number | null;
};

const GenerationTimer = ({ startTime }: { startTime: number }) => {
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => {
      setElapsed((Date.now() - startTime) / 1000);
    }, 100);
    return () => clearInterval(interval);
  }, [startTime]);

  return (
    <span className="ws-timer live">
      <LoaderCircle size={11} className="ws-spin" />
      {elapsed.toFixed(1)}s
    </span>
  );
};

const AnalysisForm = ({
  prompt,
  onPromptChange,
  selectedKb,
  onKbChange,
  file,
  kbDocuments,
  onFileChange,
  onAnalyze,
  loading,
  disableAnalyze,
  error,
  toast,
  onResetSession,
  hasAnalysis,
  duration,
  analysisStartTime,
}: AnalysisFormProps) => {
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [sourceMode, setSourceMode] = useState<'upload' | 'kb'>(selectedKb ? 'kb' : 'upload');

  // Sync sourceMode when selectedKb changes externally without useEffect
  const [prevSelectedKb, setPrevSelectedKb] = useState(selectedKb);
  if (selectedKb !== prevSelectedKb) {
    setPrevSelectedKb(selectedKb);
    if (selectedKb) setSourceMode('kb');
  }

  const hasSource = Boolean(selectedKb || file);
  const promptTrimmed = prompt.trim();

  const readinessItems = [
    {
      label: 'Sorgente definita',
      ready: hasSource,
    },
    {
      label: 'Brief del planner',
      ready: Boolean(promptTrimmed),
    },
    {
      label: 'Output strutturato',
      ready: true,
    },
  ];

  useEffect(() => {
    if (!file && fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  }, [file]);

  const handleDrop = (event: React.DragEvent<HTMLLabelElement>) => {
    event.preventDefault();
    const droppedFile = event.dataTransfer?.files?.[0];
    if (!droppedFile) return;
    const dataTransfer = new DataTransfer();
    dataTransfer.items.add(droppedFile);
    if (fileInputRef.current) {
      fileInputRef.current.files = dataTransfer.files;
      const synthetic = new Event('change', { bubbles: true });
      fileInputRef.current.dispatchEvent(synthetic);
    } else {
      onFileChange({
        target: { files: dataTransfer.files },
      } as unknown as ChangeEvent<HTMLInputElement>);
    }
  };

  const handleClearFile = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (fileInputRef.current) fileInputRef.current.value = '';
    onFileChange({ target: { files: null } } as unknown as ChangeEvent<HTMLInputElement>);
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', minHeight: 0 }}>
      <div className="ws-panel-header">
        <span className="ws-panel-label">Configurazione</span>
        {hasAnalysis && (
          <button
            className="ws-btn"
            onClick={onResetSession}
            style={{ padding: '3px 8px', fontSize: '11px' }}
          >
            <RefreshCw size={10} /> Reset
          </button>
        )}
      </div>

      <div className="ws-panel-scroll">
        {/* ── Source section ── */}
        <div className="ws-section">
          <div className="ws-section-title">Sorgente documento</div>

          {/* Tab toggle */}
          <div className="ws-source-tabs">
            <button
              className={`ws-source-tab${sourceMode === 'upload' ? ' active' : ''}`}
              onClick={() => {
                setSourceMode('upload');
                onKbChange('');
              }}
            >
              <UploadCloud size={12} />
              Upload
            </button>
            <button
              className={`ws-source-tab${sourceMode === 'kb' ? ' active' : ''}`}
              onClick={() => setSourceMode('kb')}
            >
              <Database size={12} />
              Knowledge Base
            </button>
          </div>

          {/* Upload mode */}
          {sourceMode === 'upload' && (
            <label
              className={`ws-dropzone${file ? ' has-file' : ''}`}
              onDragOver={(e) => e.preventDefault()}
              onDrop={handleDrop}
            >
              <input type="file" hidden onChange={onFileChange} ref={fileInputRef} />
              <div className="ws-dropzone-icon">
                {file ? <FileText size={14} /> : <UploadCloud size={14} />}
              </div>
              <div className="ws-dropzone-info">
                <div className="ws-dropzone-title">{file ? file.name : 'Trascina o clicca'}</div>
                <div className="ws-dropzone-hint">
                  {file ? `Pronto per l'analisi` : 'PDF, DOCX, TXT supportati'}
                </div>
              </div>
              {file && (
                <button
                  onClick={handleClearFile}
                  style={{
                    marginLeft: 'auto',
                    background: 'none',
                    border: 'none',
                    cursor: 'pointer',
                    color: 'var(--muted)',
                    padding: '2px',
                    display: 'flex',
                    flexShrink: 0,
                  }}
                >
                  <X size={14} />
                </button>
              )}
            </label>
          )}

          {/* KB mode */}
          {sourceMode === 'kb' && (
            <div className="ws-field">
              {kbDocuments.length === 0 ? (
                <div
                  style={{
                    padding: '10px 12px',
                    borderRadius: 8,
                    border: '1px solid var(--border)',
                    background: 'var(--panel)',
                    fontSize: '11.5px',
                    color: 'var(--muted)',
                    lineHeight: 1.5,
                  }}
                >
                  Nessun documento nella Knowledge Base. Carica prima un file via{' '}
                  <button
                    style={{
                      background: 'none',
                      border: 'none',
                      padding: 0,
                      color: 'var(--accent)',
                      fontWeight: 700,
                      cursor: 'pointer',
                      fontSize: 'inherit',
                      fontFamily: 'inherit',
                    }}
                    onClick={() => setSourceMode('upload')}
                  >
                    Upload
                  </button>{' '}
                  e salvalo in KB.
                </div>
              ) : (
                <select
                  className="ws-select"
                  value={selectedKb}
                  onChange={(e) => onKbChange(e.target.value)}
                >
                  <option value="">Seleziona documento...</option>
                  {kbDocuments.map((doc) => (
                    <option key={doc.path} value={doc.path}>
                      {doc.label || doc.path}
                    </option>
                  ))}
                </select>
              )}
            </div>
          )}
        </div>

        {/* ── Brief section ── */}
        <div className="ws-section">
          <div className="ws-section-title">Brief planner</div>
          <div className="ws-field">
            <textarea
              className="ws-textarea"
              value={prompt}
              onChange={(e) => onPromptChange(e.target.value)}
              placeholder="Obiettivi, vincoli, priorità o contesto per il backlog..."
              rows={5}
            />
            {promptTrimmed && (
              <span style={{ fontSize: '10.5px', color: 'var(--muted)', textAlign: 'right' }}>
                {promptTrimmed.length} caratteri
              </span>
            )}
          </div>
        </div>

        {/* ── Readiness checklist ── */}
        <div className="ws-section">
          <div className="ws-section-title">Checklist</div>
          <div className="ws-checklist">
            {readinessItems.map((item) => (
              <div key={item.label} className={`ws-check-item${item.ready ? ' ready' : ''}`}>
                <div className="ws-check-marker">{item.ready && <CheckCircle size={10} />}</div>
                <span className="ws-check-label">{item.label}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Error display */}
        {error && (
          <div className="ws-section">
            <div className="ws-alert">{error}</div>
          </div>
        )}
      </div>

      {/* ── Sticky footer: Run button ── */}
      <div className="ws-panel-footer">
        <button className="ws-run-btn" onClick={onAnalyze} disabled={disableAnalyze}>
          {loading ? <Loader2 size={15} className="ws-spin" /> : <Wand2 size={15} />}
          {loading ? 'Analisi in corso…' : 'Esegui Planner'}
        </button>

        {loading && analysisStartTime && <GenerationTimer startTime={analysisStartTime} />}

        {!loading && hasAnalysis && duration !== undefined && (
          <span className="ws-timer">Completato in {duration.toFixed(1)}s</span>
        )}
      </div>

      <FloatingToast payload={toast} />
    </div>
  );
};

export default AnalysisForm;
