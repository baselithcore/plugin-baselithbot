/**
 * TraceViewer - Attack Trace Inspector Modal
 *
 * Modern, polished UI for viewing pentest attack traces.
 * Features glassmorphism, smooth animations, and proper empty states.
 */

import React, { useState, useMemo } from 'react';
import { AttackTrace } from '../../types';
import {
  X,
  CheckCircle,
  XCircle,
  Search,
  ChevronDown,
  AlertCircle,
  Shield,
  Zap,
  FileWarning,
  Copy,
  Check,
} from 'lucide-react';
import './PentestTab.css';

interface TraceViewerProps {
  traces: AttackTrace[];
  onClose: () => void;
}

const TraceViewer: React.FC<TraceViewerProps> = ({ traces, onClose }) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedTraceId, setSelectedTraceId] = useState<string | null>(
    traces.length > 0 ? traces[0].trace_id : null
  );
  const [copiedPayload, setCopiedPayload] = useState(false);
  const [copiedResponse, setCopiedResponse] = useState(false);

  const filteredTraces = useMemo(() => {
    if (!searchTerm.trim()) return traces;
    const term = searchTerm.toLowerCase();
    return traces.filter(
      (t) =>
        t.vector_name.toLowerCase().includes(term) ||
        t.payload_sent.toLowerCase().includes(term) ||
        t.status.toLowerCase().includes(term)
    );
  }, [traces, searchTerm]);

  const selectedTrace = useMemo(() => {
    if (!selectedTraceId) return traces[0] || null;
    return traces.find((t) => t.trace_id === selectedTraceId) || traces[0] || null;
  }, [traces, selectedTraceId]);

  // Stats for header
  const stats = useMemo(() => {
    const blocked = traces.filter((t) => t.status === 'BLOCKED').length;
    const success = traces.filter((t) => t.status === 'SUCCESS').length;
    const failed = traces.filter((t) => t.status === 'FAILED').length;
    return { blocked, success, failed, total: traces.length };
  }, [traces]);

  const handleCopy = async (text: string, type: 'payload' | 'response') => {
    try {
      await navigator.clipboard.writeText(text);
      if (type === 'payload') {
        setCopiedPayload(true);
        setTimeout(() => setCopiedPayload(false), 2000);
      } else {
        setCopiedResponse(true);
        setTimeout(() => setCopiedResponse(false), 2000);
      }
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'BLOCKED':
        return <Shield size={14} className="status-icon status-blocked" />;
      case 'SUCCESS':
        return <AlertCircle size={14} className="status-icon status-success" />;
      case 'FAILED':
        return <XCircle size={14} className="status-icon status-failed" />;
      default:
        return <Zap size={14} className="status-icon" />;
    }
  };

  const getStatusClass = (status: string) => {
    switch (status) {
      case 'BLOCKED':
        return 'hp-status--blocked';
      case 'SUCCESS':
        return 'hp-status--success';
      case 'FAILED':
        return 'hp-status--failed';
      default:
        return '';
    }
  };

  // Handle close on escape key
  React.useEffect(() => {
    const handleEsc = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handleEsc);
    return () => window.removeEventListener('keydown', handleEsc);
  }, [onClose]);

  return (
    <div className="hp-modal-overlay" onClick={onClose}>
      <div className="hp-trace-viewer" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="hp-trace-header">
          <div className="hp-trace-title">
            <div className="hp-trace-title-icon">
              <Shield size={20} />
            </div>
            <div>
              <h3>Attack Trace Inspector</h3>
              <p className="hp-trace-subtitle">
                Study mode: analyze attack patterns and defense responses
              </p>
            </div>
          </div>

          {/* Quick Stats */}
          {traces.length > 0 && (
            <div className="hp-trace-quick-stats">
              <div className="hp-qs-item hp-qs-blocked">
                <Shield size={14} />
                <span>{stats.blocked}</span>
              </div>
              <div className="hp-qs-item hp-qs-success">
                <AlertCircle size={14} />
                <span>{stats.success}</span>
              </div>
              <div className="hp-qs-item hp-qs-total">
                <span>{stats.total} total</span>
              </div>
            </div>
          )}

          <button className="hp-trace-close" onClick={onClose}>
            <X size={20} />
          </button>
        </div>

        {/* Check if traces exist */}
        {traces.length === 0 ? (
          <div className="hp-trace-empty">
            <div className="hp-trace-empty-icon">
              <FileWarning size={64} />
            </div>
            <h4>No Attack Traces Available</h4>
            <p>
              This pentest result doesn't have any attack traces recorded. This can happen with
              older results or if trace recording was disabled.
            </p>
            <div className="hp-trace-empty-hints">
              <div className="hp-hint-item">
                <CheckCircle size={16} />
                <span>Run a new pentest to generate fresh traces</span>
              </div>
              <div className="hp-hint-item">
                <CheckCircle size={16} />
                <span>Traces show the exact request/response for each attack</span>
              </div>
            </div>
            <button className="hp-btn hp-btn-secondary" onClick={onClose}>
              Close Inspector
            </button>
          </div>
        ) : (
          <div className="hp-trace-layout">
            {/* Left Sidebar: Trace List */}
            <div className="hp-trace-sidebar">
              <div className="hp-trace-search">
                <Search size={16} />
                <input
                  type="text"
                  placeholder="Search traces..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                />
                {searchTerm && (
                  <button
                    className="hp-search-clear"
                    onClick={() => setSearchTerm('')}
                    title="Clear search"
                  >
                    <X size={14} />
                  </button>
                )}
              </div>

              <div className="hp-trace-list">
                {filteredTraces.length === 0 ? (
                  <div className="hp-trace-no-results">
                    <Search size={24} />
                    <p>No traces match your search</p>
                    <button onClick={() => setSearchTerm('')}>Clear search</button>
                  </div>
                ) : (
                  filteredTraces.map((trace, index) => (
                    <div
                      key={trace.trace_id}
                      className={`hp-trace-item ${
                        selectedTrace?.trace_id === trace.trace_id ? 'active' : ''
                      } ${getStatusClass(trace.status)}`}
                      onClick={() => setSelectedTraceId(trace.trace_id)}
                    >
                      <div className="hp-trace-item-number">{index + 1}</div>
                      <div className="hp-trace-item-status">{getStatusIcon(trace.status)}</div>
                      <div className="hp-trace-item-info">
                        <span className="hp-trace-item-name">{trace.vector_name}</span>
                        <span className="hp-trace-item-meta">
                          {trace.mutation_info || 'Direct Attack'}
                        </span>
                      </div>
                      <div className={`hp-trace-item-badge ${getStatusClass(trace.status)}`}>
                        {trace.status}
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>

            {/* Right Panel: Detail View */}
            <div className="hp-trace-detail">
              {selectedTrace ? (
                <div className="hp-trace-content">
                  {/* Vector Info Header */}
                  <div className="hp-trace-vector-header">
                    <h4>{selectedTrace.vector_name}</h4>
                    <div
                      className={`hp-trace-vector-status ${getStatusClass(selectedTrace.status)}`}
                    >
                      {getStatusIcon(selectedTrace.status)}
                      <span>{selectedTrace.status}</span>
                    </div>
                  </div>

                  {selectedTrace.mutation_info && (
                    <div className="hp-trace-mutation">
                      <Zap size={14} />
                      <span>Mutation Applied: {selectedTrace.mutation_info}</span>
                    </div>
                  )}

                  {/* Attacker Message */}
                  <div className="hp-trace-message hp-trace-message--attacker">
                    <div className="hp-trace-message-header">
                      <div className="hp-trace-role">
                        <div className="hp-role-icon hp-role-attacker">
                          <AlertCircle size={16} />
                        </div>
                        <span>Attacker Payload</span>
                      </div>
                      <div className="hp-trace-message-actions">
                        <button
                          className="hp-copy-btn"
                          onClick={() => handleCopy(selectedTrace.payload_sent, 'payload')}
                          title="Copy payload"
                        >
                          {copiedPayload ? <Check size={14} /> : <Copy size={14} />}
                        </button>
                        <span className="hp-trace-timestamp">
                          {new Date(selectedTrace.timestamp).toLocaleTimeString()}
                        </span>
                      </div>
                    </div>
                    <div className="hp-trace-message-body">
                      <pre>{selectedTrace.payload_sent}</pre>
                    </div>
                  </div>

                  {/* Flow Indicator */}
                  <div className="hp-trace-flow">
                    <div className="hp-flow-line"></div>
                    <ChevronDown size={20} />
                    <div className="hp-flow-line"></div>
                  </div>

                  {/* Target Response */}
                  <div className="hp-trace-message hp-trace-message--target">
                    <div className="hp-trace-message-header">
                      <div className="hp-trace-role">
                        <div className="hp-role-icon hp-role-target">
                          <Shield size={16} />
                        </div>
                        <span>Target Response</span>
                      </div>
                      <div className="hp-trace-message-actions">
                        <button
                          className="hp-copy-btn"
                          onClick={() => handleCopy(selectedTrace.response_received, 'response')}
                          title="Copy response"
                        >
                          {copiedResponse ? <Check size={14} /> : <Copy size={14} />}
                        </button>
                      </div>
                    </div>
                    <div className="hp-trace-message-body">
                      <pre>{selectedTrace.response_received}</pre>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="hp-trace-select-prompt">
                  <Shield size={48} />
                  <p>Select a trace from the list to view details</p>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default TraceViewer;
