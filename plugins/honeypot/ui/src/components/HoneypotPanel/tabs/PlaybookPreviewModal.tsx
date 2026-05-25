import React, { useState } from 'react';
import { Eye, X, Loader2, Play, Dna, Link2, ChevronDown, Copy, Check } from 'lucide-react';
import type { PentestPlaybook } from '../../types';
import './PentestTab.css';

interface PlaybookPreviewModalProps {
  playbook: PentestPlaybook;
  onClose: () => void;
  onRun: (id: string) => void;
  isRunning: boolean;
}

export const PlaybookPreviewModal: React.FC<PlaybookPreviewModalProps> = ({
  playbook,
  onClose,
  onRun,
  isRunning,
}) => {
  const [expandedVector, setExpandedVector] = useState<number | null>(null);
  const [copiedPayload, setCopiedPayload] = useState<number | null>(null);

  const analyzePlaybook = (pb: PentestPlaybook) => {
    const counts: Record<string, number> = {};
    let mutationCount = 0;
    let multiTurnCount = 0;

    pb.attack_vectors.forEach((v) => {
      counts[v.category] = (counts[v.category] || 0) + 1;
      if (v.name.startsWith('mutated_')) mutationCount++;
      if (v.name.startsWith('social_eng_')) multiTurnCount++;
    });

    return { counts, mutationCount, multiTurnCount };
  };

  const analysis = analyzePlaybook(playbook);

  const toggleVector = (idx: number) => {
    setExpandedVector(expandedVector === idx ? null : idx);
  };

  const handleCopy = (text: string, idx: number, e: React.MouseEvent) => {
    e.stopPropagation();
    navigator.clipboard.writeText(text);
    setCopiedPayload(idx);
    setTimeout(() => setCopiedPayload(null), 2000);
  };

  const getCategoryColor = (cat: string) => {
    const lower = cat.toLowerCase();
    if (lower.includes('injection')) return 'var(--hp-danger)';
    if (lower.includes('social')) return '#9b59b6'; // Purple
    if (lower.includes('escalation')) return '#e67e22'; // Orange
    if (lower.includes('extraction')) return '#f1c40f'; // Yellow
    if (lower.includes('scan')) return '#3498db'; // Blue
    return 'var(--hp-cyan)';
  };

  return (
    <div className="hp-modal-overlay" onClick={onClose}>
      <div className="hp-modal hp-modal--preview" onClick={(e) => e.stopPropagation()}>
        <div className="hp-modal-header">
          <h3>
            <Eye size={18} /> Playbook Preview
          </h3>
          <button className="hp-modal-close" onClick={onClose}>
            <X size={18} />
          </button>
        </div>
        <div className="hp-modal-body">
          <div className="hp-preview-header-content">
            <div className="hp-preview-meta">
              <h4>{playbook.name}</h4>
              <p>{playbook.attack_vectors.length} vectors generated</p>
            </div>

            <div className="hp-preview-stats-grid">
              {analysis.mutationCount > 0 && (
                <div className="hp-stat-pill hp-stat-pill--mutation">
                  <Dna size={14} />
                  <span>{analysis.mutationCount} Mutations</span>
                </div>
              )}
              {analysis.multiTurnCount > 0 && (
                <div className="hp-stat-pill hp-stat-pill--complex">
                  <Link2 size={14} />
                  <span>{analysis.multiTurnCount} Multi-Stage</span>
                </div>
              )}
              {Object.entries(analysis.counts).map(([cat, count]) => (
                <div
                  key={cat}
                  className="hp-stat-pill"
                  style={{ borderColor: getCategoryColor(cat), color: getCategoryColor(cat) }}
                >
                  <span>
                    {count} {cat.toLowerCase().replace(/_/g, ' ')}
                  </span>
                </div>
              ))}
            </div>
          </div>

          <div className="hp-preview-vectors">
            <div className="hp-vectors-list">
              {playbook.attack_vectors.slice(0, 50).map((v, idx) => {
                const catColor = getCategoryColor(v.category);
                return (
                  <div
                    key={idx}
                    className={`hp-vector-item ${expandedVector === idx ? 'active' : ''}`}
                    onClick={() => toggleVector(idx)}
                    style={{ borderLeftColor: catColor }}
                  >
                    <div className="hp-vector-header-row">
                      <span className="hp-vector-name" title={v.name}>
                        {v.name}
                      </span>
                      <span
                        className="hp-vector-category-badge"
                        style={{ backgroundColor: `${catColor}20`, color: catColor }}
                      >
                        {v.category.replace(/_/g, ' ')}
                      </span>
                      <ChevronDown size={16} className="hp-vector-chevron" />
                    </div>

                    <div className="hp-vector-summary-payload">{v.payload.slice(0, 60)}...</div>

                    {expandedVector === idx && (
                      <div className="hp-vector-details" onClick={(e) => e.stopPropagation()}>
                        <div className="hp-details-actions">
                          <span className="hp-vector-label">Payload content</span>
                          <button
                            className="hp-copy-btn-mini"
                            onClick={(e) => handleCopy(v.payload, idx, e)}
                          >
                            {copiedPayload === idx ? <Check size={14} /> : <Copy size={14} />}
                            {copiedPayload === idx ? 'Copied' : 'Copy'}
                          </button>
                        </div>
                        <div className="hp-vector-full-payload">{v.payload}</div>
                      </div>
                    )}
                  </div>
                );
              })}
              {playbook.attack_vectors.length > 50 && (
                <div className="hp-vectors-more">
                  +{playbook.attack_vectors.length - 50} more vectors
                </div>
              )}
            </div>
          </div>
        </div>
        <div className="hp-modal-footer">
          <button className="hp-btn hp-btn-secondary" onClick={onClose}>
            Close Preview
          </button>
          <button
            className="hp-btn hp-btn-run"
            onClick={() => onRun(playbook.playbook_id)}
            disabled={isRunning}
          >
            {isRunning ? <Loader2 size={14} className="spin" /> : <Play size={14} />}
            Start Pentest
          </button>
        </div>
      </div>
    </div>
  );
};
