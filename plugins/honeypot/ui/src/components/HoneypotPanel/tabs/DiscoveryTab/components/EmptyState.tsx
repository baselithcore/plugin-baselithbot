import { Network, RefreshCw } from 'lucide-react';

import './EmptyState.css';

interface EmptyStateProps {
  onRunAnalysis: () => void;
}

export function EmptyState({ onRunAnalysis }: EmptyStateProps) {
  return (
    <div className="discovery-empty-state">
      <Network size={48} />
      <h3>No Analysis Available</h3>
      <p>
        Run a discovery analysis to detect threats, zero-days, and generate threat intelligence.
      </p>
      <button className="discovery-analyze-btn" onClick={onRunAnalysis}>
        <RefreshCw size={14} />
        Run First Analysis
      </button>
    </div>
  );
}
