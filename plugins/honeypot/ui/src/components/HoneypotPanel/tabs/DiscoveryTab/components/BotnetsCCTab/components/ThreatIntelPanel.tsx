import { Target, Globe, Link, Hash, FileCode, Download } from 'lucide-react';
import { IOCCard } from '../../SinkholeMonitor/cards/IOCCard';
import { EmptyState as SinkholeEmptyState } from '../../SinkholeMonitor/components/EmptyState';

interface IOCCount {
  ips: number;
  domains: number;
  hashes: number;
}

interface ThreatIntelPanelProps {
  hasIntelData: boolean;
  confidence: number;
  severity: string;
  attackTypes: string[];
  iocCount: IOCCount;
  yaraCount: number;
  onOpenIOCModal: (category: 'ips' | 'domains' | 'hashes' | 'yara' | null) => void;
}

export function ThreatIntelPanel({
  hasIntelData,
  confidence,
  severity,
  attackTypes,
  iocCount,
  yaraCount,
  onOpenIOCModal,
}: ThreatIntelPanelProps) {
  if (!hasIntelData) {
    return <SinkholeEmptyState icon={<Target />} message="No threat intelligence data available" />;
  }

  return (
    <>
      <div className="threat-overview">
        <div className="threat-overview-row">
          <div className="threat-confidence">
            <div className="threat-confidence-label">
              <span>Confidence</span>
              <span>{(confidence * 100).toFixed(0)}%</span>
            </div>
            <div className="threat-confidence-bar">
              <div className="threat-confidence-fill" style={{ width: `${confidence * 100}%` }} />
            </div>
          </div>
          <div className="threat-severity">
            <span className={`threat-severity-badge ${severity}`}>{severity}</span>
          </div>
        </div>
        {attackTypes.length > 0 && (
          <div className="threat-attack-types">
            {attackTypes.slice(0, 5).map((type: string, i: number) => (
              <span key={i} className="threat-attack-tag">
                {type.replace(/_/g, ' ')}
              </span>
            ))}
          </div>
        )}
      </div>

      {/* IOC Cards */}
      <div className="ioc-grid" style={{ marginTop: '1rem' }}>
        <IOCCard
          icon={<Globe />}
          value={iocCount.ips}
          label="Malicious IPs"
          variant="ips"
          onClick={() => iocCount.ips > 0 && onOpenIOCModal('ips')}
          disabled={iocCount.ips === 0}
        />
        <IOCCard
          icon={<Link />}
          value={iocCount.domains}
          label="Domains"
          variant="domains"
          onClick={() => iocCount.domains > 0 && onOpenIOCModal('domains')}
          disabled={iocCount.domains === 0}
        />
        <IOCCard
          icon={<Hash />}
          value={iocCount.hashes}
          label="Hashes"
          variant="hashes"
          onClick={() => iocCount.hashes > 0 && onOpenIOCModal('hashes')}
          disabled={iocCount.hashes === 0}
        />
        <IOCCard
          icon={<FileCode />}
          value={yaraCount}
          label="YARA Rules"
          variant="yara"
          onClick={() => yaraCount > 0 && onOpenIOCModal('yara')}
          disabled={yaraCount === 0}
        />
      </div>

      {/* Export Button */}
      <button
        className="export-btn"
        onClick={() => onOpenIOCModal(null)}
        style={{ marginTop: '1rem', width: '100%' }}
      >
        <Download />
        Export Threat Intel
      </button>
    </>
  );
}
