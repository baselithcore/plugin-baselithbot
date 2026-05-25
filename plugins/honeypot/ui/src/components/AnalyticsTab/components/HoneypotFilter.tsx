import { Filter } from 'lucide-react';
import type { HoneypotInfo } from '../../types';

interface HoneypotFilterProps {
  selectedHoneypot: string;
  honeypots: HoneypotInfo[];
  onFilterChange: (e: React.ChangeEvent<HTMLSelectElement>) => void;
}

export function HoneypotFilter({
  selectedHoneypot,
  honeypots,
  onFilterChange,
}: HoneypotFilterProps) {
  return (
    <div
      className="analytics-toolbar"
      style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: '10px' }}
    >
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '10px',
          background: 'rgba(255,255,255,0.05)',
          padding: '8px 16px',
          borderRadius: '8px',
          border: '1px solid rgba(255,255,255,0.1)',
        }}
      >
        <Filter size={16} color="#8892b0" />
        <span style={{ color: '#8892b0', fontSize: '0.9rem' }}>Filter by ATLAS:</span>
        <select
          value={selectedHoneypot}
          onChange={onFilterChange}
          style={{
            background: 'transparent',
            border: 'none',
            color: '#fff',
            fontSize: '0.9rem',
            outline: 'none',
            cursor: 'pointer',
            minWidth: '150px',
          }}
        >
          <option value="all">All ATLAS</option>
          {honeypots.map((hp) => (
            <option key={hp.id} value={hp.id}>
              {hp.name} ({hp.protocol})
            </option>
          ))}
        </select>
      </div>
    </div>
  );
}
