import React from 'react';
import { Zap, Settings, FileText, Loader2, Play, Eye, Dna, Link2, Trash2 } from 'lucide-react';
import type { PentestPlaybook } from '../../types';
import { CATEGORY_ICONS } from './constants';
import './PentestTab.css';

interface PlaybookListProps {
  playbooks: PentestPlaybook[];
  isLoading: boolean;
  onGenerateNew: () => void;
  onRunPentest: (id: string) => void;
  runningPlaybookId: string | null;
  onPreview: (playbook: PentestPlaybook) => void;
  onDelete: (id: string) => void;
  deletingPlaybookId: string | null;
}

export const PlaybookList: React.FC<PlaybookListProps> = ({
  playbooks,
  isLoading,
  onGenerateNew,
  onRunPentest,
  runningPlaybookId,
  onPreview,
  onDelete,
  deletingPlaybookId,
}) => {
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

  return (
    <div className="hp-pentest-section">
      <div className="hp-section-header">
        <h3>
          <Zap size={16} /> Attack Playbooks
        </h3>
        <button className="hp-btn hp-btn-primary hp-btn-glow" onClick={onGenerateNew}>
          <Settings size={14} /> Generate New
        </button>
      </div>

      <div className="hp-playbook-list">
        {isLoading ? (
          <div className="hp-loading-state">
            <Loader2 size={24} className="spin" /> Loading playbooks...
          </div>
        ) : playbooks.length === 0 ? (
          <div className="hp-empty-state hp-empty-state--animated">
            <div className="hp-empty-icon">
              <FileText size={48} />
            </div>
            <p>No playbooks yet.</p>
            <button className="hp-btn hp-btn-primary hp-btn-glow" onClick={onGenerateNew}>
              <Zap size={14} /> Generate Your First Playbook
            </button>
          </div>
        ) : (
          playbooks.map((pb) => {
            const analysis = analyzePlaybook(pb);
            return (
              <div key={pb.playbook_id} className="hp-playbook-card hp-playbook-card--enhanced">
                <div className="hp-playbook-info">
                  <h4>{pb.name}</h4>
                  <div className="hp-playbook-meta">
                    <span className="hp-playbook-vectors">{pb.attack_vectors.length} vectors</span>
                    <span className="hp-playbook-date">
                      {new Date(pb.created_at).toLocaleDateString()}
                    </span>
                  </div>
                  <div className="hp-playbook-badges">
                    {analysis.mutationCount > 0 && (
                      <span className="hp-badge hp-badge--fuzzing">
                        <Dna size={10} /> {analysis.mutationCount} Fuzzing
                      </span>
                    )}
                    {analysis.multiTurnCount > 0 && (
                      <span className="hp-badge hp-badge--multiturn">
                        <Link2 size={10} /> {analysis.multiTurnCount} Multi-Turn
                      </span>
                    )}
                    {Object.entries(analysis.counts)
                      .slice(0, 2)
                      .map(([cat, count]) => {
                        const catInfo = CATEGORY_ICONS[cat];
                        return catInfo ? (
                          <span
                            key={cat}
                            className="hp-badge"
                            style={{ background: `${catInfo.color}22`, color: catInfo.color }}
                          >
                            {catInfo.icon} {count}
                          </span>
                        ) : null;
                      })}
                  </div>
                </div>
                <div className="hp-playbook-actions">
                  <button
                    className="hp-btn hp-btn-ghost"
                    onClick={() => onPreview(pb)}
                    title="Preview Playbook"
                  >
                    <Eye size={16} />
                  </button>
                  <button
                    className="hp-btn hp-btn-run"
                    onClick={() => onRunPentest(pb.playbook_id)}
                    disabled={runningPlaybookId === pb.playbook_id}
                  >
                    {runningPlaybookId === pb.playbook_id ? (
                      <Loader2 size={14} className="spin" />
                    ) : (
                      <Play size={14} />
                    )}
                    Run
                  </button>
                  <button
                    className="hp-btn hp-btn-ghost hp-btn-danger"
                    onClick={() => {
                      if (window.confirm(`Delete playbook "${pb.name}"? This cannot be undone.`)) {
                        onDelete(pb.playbook_id);
                      }
                    }}
                    disabled={deletingPlaybookId === pb.playbook_id}
                    title="Delete Playbook"
                  >
                    {deletingPlaybookId === pb.playbook_id ? (
                      <Loader2 size={14} className="spin" />
                    ) : (
                      <Trash2 size={14} />
                    )}
                  </button>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
