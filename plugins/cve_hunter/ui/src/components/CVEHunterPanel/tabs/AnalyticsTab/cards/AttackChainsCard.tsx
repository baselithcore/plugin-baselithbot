/**
 * AttackChainsCard - Attack Chains Detection Card
 */

import { AlertTriangle } from 'lucide-react';
import type { AttackChain } from '../../../../api';

interface AttackChainsCardProps {
  attackChains: AttackChain[];
  onChainClick: (chain: AttackChain) => void;
  onCVEClickById: (cveId: string) => void;
}

export const AttackChainsCard = ({
  attackChains,
  onChainClick,
  onCVEClickById,
}: AttackChainsCardProps) => {
  return (
    <div className="glass-card">
      <div className="glass-card-header">
        <span className="glass-card-title">
          <AlertTriangle size={16} color="var(--cyber-neon-pink)" />
          Attack Chains Detected
        </span>
        <span className="glass-card-badge">LIVE</span>
      </div>
      <div style={{ padding: '0 15px 10px 15px', color: '#888', fontSize: '11px' }}>
        Autonomously identified by Correlator Agent based on MITRE ATT&CK patterns.
      </div>
      <div className="attack-chain-list">
        {attackChains.length > 0 ? (
          attackChains.map((chain) => (
            <div
              key={chain.chain_id}
              className="attack-chain-item"
              onClick={() => onChainClick(chain)}
              style={{ cursor: 'pointer' }}
            >
              <div className="attack-chain-name">🔗 {chain.name}</div>
              <div className="attack-chain-cves">
                {chain.cve_ids.map((cveId) => (
                  <span
                    key={cveId}
                    className="chain-cve-tag"
                    onClick={(e) => {
                      e.stopPropagation();
                      onCVEClickById(cveId);
                    }}
                  >
                    {cveId}
                  </span>
                ))}
              </div>
            </div>
          ))
        ) : (
          <div className="empty-state-premium">
            <div className="empty-state-icon">🔗</div>
            <div className="empty-state-text">
              No attack chains detected yet.
              <br />
              Run a scan to analyze CVE correlations.
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
