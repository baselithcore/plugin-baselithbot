import { X, Activity, Link, Layers } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import { useState } from 'react';
import { AttackChain, analyzeAttackChain } from './api';
import './CVEHunterPanel/CVEHunterPanel.css';

interface AttackChainModalProps {
  chain: AttackChain;
  onClose: () => void;
  onCveClick: (cveId: string) => void;
}

const AttackChainModal = ({ chain: initialChain, onClose, onCveClick }: AttackChainModalProps) => {
  const [chain, setChain] = useState<AttackChain>(initialChain);
  const [isAnalyzing, setIsAnalyzing] = useState(false);

  const [error, setError] = useState<string | null>(null);

  const handleAnalyze = async () => {
    setIsAnalyzing(true);
    setError(null);
    try {
      const updatedChain = await analyzeAttackChain(chain.chain_id);
      if (updatedChain.error) {
        setError(updatedChain.error);
      } else {
        setChain(updatedChain);
      }
    } catch (err: any) {
      console.error('Chain analysis failed:', err);
      setError(err.message || 'Analysis failed to connect to server');
    } finally {
      setIsAnalyzing(false);
    }
  };

  return (
    <div className="cve-modal-backdrop" onClick={onClose}>
      <div className="cve-modal-content premium-modal" onClick={(e) => e.stopPropagation()}>
        <header className="cve-modal-header glass-header">
          <div className="header-left">
            <div className="chain-icon-badge">
              <Link size={20} />
            </div>
            <div>
              <div className="overline">Attack Chain Detected</div>
              <h2>{chain.name}</h2>
            </div>
          </div>

          <div className="header-right">
            <div className="severity-badge-large critical">
              <span className="label">SEVERITY</span>
              <span className="value">{chain.total_severity.toFixed(1)}</span>
            </div>
            <button className="cve-modal-close-premium" onClick={onClose}>
              <X size={20} />
            </button>
          </div>
        </header>

        <div className="cve-modal-body">
          <div className="modal-grid">
            {/* Left Column: Description & MITRE */}
            <div className="modal-col-left">
              <section className="cve-section">
                <h3>Description</h3>
                <p className="description-text">{chain.description}</p>
              </section>

              <section className="cve-section techniques-section">
                <h3>MITRE ATT&CK Techniques</h3>
                <div className="techniques-grid">
                  {chain.mitre_techniques.map((tech) => (
                    <span key={tech} className="technique-pill">
                      {tech}
                    </span>
                  ))}
                </div>
              </section>
            </div>

            {/* Right Column: Attack Path */}
            <div className="modal-col-right">
              <section className="cve-section">
                <h3>
                  <Layers size={16} /> Attack Path
                </h3>
                <div className="chain-timeline">
                  {chain.cve_ids.map((cveId, index) => (
                    <div key={cveId} className="timeline-item" onClick={() => onCveClick(cveId)}>
                      <div className="timeline-marker">{index + 1}</div>
                      <div className="timeline-content">
                        <span className="cve-id">{cveId}</span>
                        {chain.stages && chain.stages[index] && chain.stages[index].cwe && (
                          <span className="cwe-tag">{chain.stages[index].cwe.join(', ')}</span>
                        )}
                      </div>
                      {index < chain.cve_ids.length - 1 && <div className="timeline-connector" />}
                    </div>
                  ))}
                </div>
              </section>
            </div>
          </div>

          {/* Bottom Section: AI Analysis (Full Width) */}
          <div className="modal-bottom-section">
            {error && (
              <div className="error-card">
                <div className="error-header">
                  <span className="error-icon">⚠️</span>
                  <strong>Analysis Failed</strong>
                </div>
                <div className="error-body">{error}</div>
              </div>
            )}

            <section className="cve-section ai-analysis-wrapper full-width">
              <div className="ai-header">
                <h3>
                  <Activity size={16} /> Kill Chain Intelligence
                </h3>
                {(!chain.ai_analysis || error) && !isAnalyzing && (
                  <button className="mini-analyze-btn" onClick={handleAnalyze}>
                    {error ? 'Retry' : 'Analyze'}
                  </button>
                )}
              </div>

              <div className="ai-content-box full-height">
                {isAnalyzing ? (
                  <div className="loader-container">
                    <div className="loader-spin" />
                    <span className="blink">Analyzing Chain Strategy...</span>
                  </div>
                ) : chain.ai_analysis ? (
                  <div className="markdown-body premium-md">
                    <ReactMarkdown>{chain.ai_analysis}</ReactMarkdown>
                  </div>
                ) : (
                  <div className="empty-analysis">
                    <p>Run AI analysis to get a tactical breakdown of this attack chain.</p>
                  </div>
                )}
              </div>
            </section>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AttackChainModal;
