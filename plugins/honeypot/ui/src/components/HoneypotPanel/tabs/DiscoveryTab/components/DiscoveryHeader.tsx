import { Network, RefreshCw } from 'lucide-react';
import type { DiscoveryResult } from '../../../../types';
import { formatDate } from '../utils';

interface DiscoveryHeaderProps {
  result: DiscoveryResult | null;
  analyzing: boolean;
  onRunAnalysis: () => void;
}

export function DiscoveryHeader({ result, analyzing, onRunAnalysis }: DiscoveryHeaderProps) {
  return (
    <div className="discovery-header">
      <div className="discovery-header-left">
        <Network size={20} />
        <h2>Threat Discovery</h2>
        {result && (
          <span className="discovery-timestamp">
            Last analyzed: {formatDate(result.analyzed_at)}
          </span>
        )}
      </div>
      <button
        className={`discovery-analyze-btn ${analyzing ? 'analyzing' : ''}`}
        onClick={onRunAnalysis}
        disabled={analyzing}
      >
        <RefreshCw size={14} className={analyzing ? 'spinning' : ''} />
        {analyzing ? 'Analyzing...' : 'Run Analysis'}
      </button>
    </div>
  );
}
