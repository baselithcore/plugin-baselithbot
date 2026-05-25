/**
 * ThreatMetadata - Event metadata display component
 * Shows structured metadata: Session ID, Honeypot, Protocol, Event ID
 */

import { AttackEvent } from '../../../types';
import { Clock, FileText, Server, Network, Hash } from 'lucide-react';

interface ThreatMetadataProps {
  event: AttackEvent;
}

export function ThreatMetadata({ event }: ThreatMetadataProps) {
  return (
    <div className="hp-detail-col meta">
      <div
        className="hp-detail-header"
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          color: '#8892b0',
          marginBottom: '8px',
          textTransform: 'uppercase',
          fontSize: '11px',
          letterSpacing: '1px',
          fontWeight: 700,
        }}
      >
        <Clock size={14} />
        <span>Event Metadata</span>
      </div>
      <div
        className="hp-meta-list"
        style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}
      >
        {/* Session ID */}
        <div className="hp-meta-item" style={{ display: 'flex', gap: '12px' }}>
          <FileText size={14} style={{ color: '#555', marginTop: '2px' }} />
          <div className="hp-meta-content">
            <label
              style={{
                display: 'block',
                fontSize: '11px',
                color: '#555',
                marginBottom: '2px',
              }}
            >
              Session ID
            </label>
            <span
              style={{
                fontFamily: 'monospace',
                fontSize: '12px',
                color: '#ccc',
              }}
            >
              {event.session_id}
            </span>
          </div>
        </div>

        {/* Honeypot */}
        <div className="hp-meta-item" style={{ display: 'flex', gap: '12px' }}>
          <Server size={14} style={{ color: '#555', marginTop: '2px' }} />
          <div className="hp-meta-content">
            <label
              style={{
                display: 'block',
                fontSize: '11px',
                color: '#555',
                marginBottom: '2px',
              }}
            >
              Honeypot
            </label>
            <span style={{ fontSize: '12px', color: '#ccc' }}>{event.honeypot_id}</span>
          </div>
        </div>

        {/* Protocol */}
        <div className="hp-meta-item" style={{ display: 'flex', gap: '12px' }}>
          <Network size={14} style={{ color: '#555', marginTop: '2px' }} />
          <div className="hp-meta-content">
            <label
              style={{
                display: 'block',
                fontSize: '11px',
                color: '#555',
                marginBottom: '2px',
              }}
            >
              Protocol
            </label>
            <span style={{ fontSize: '12px', color: '#ccc' }}>{event.protocol}</span>
          </div>
        </div>

        {/* Event ID */}
        <div className="hp-meta-item" style={{ display: 'flex', gap: '12px' }}>
          <Hash size={14} style={{ color: '#555', marginTop: '2px' }} />
          <div className="hp-meta-content">
            <label
              style={{
                display: 'block',
                fontSize: '11px',
                color: '#555',
                marginBottom: '2px',
              }}
            >
              Event ID
            </label>
            <span
              style={{
                fontFamily: 'monospace',
                fontSize: '12px',
                color: '#ccc',
              }}
            >
              {event.event_id}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
