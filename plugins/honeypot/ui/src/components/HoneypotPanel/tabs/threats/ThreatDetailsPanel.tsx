/**
 * ThreatDetailsPanel - Expanded threat details component
 * Shows payload, CVEs, patterns, and metadata when a row is expanded
 */

import { AttackEvent } from '../../../types';
import { Code, ShieldAlert, Hash, ExternalLink } from 'lucide-react';
import { CopyButton } from './utils/CopyButton';
import { ThreatMetadata } from './ThreatMetadata';

interface ThreatDetailsPanelProps {
  event: AttackEvent;
  onSelectAttack: (event: AttackEvent) => void;
}

export function ThreatDetailsPanel({ event, onSelectAttack }: ThreatDetailsPanelProps) {
  const hasPayload = event.raw_data || event.command || event.http_path;
  const payloadPre = event.command || event.http_path || event.raw_data || '';

  return (
    <div
      className="hp-threat-details-panel"
      style={{
        background: '#0f0f15',
        padding: '20px',
        borderBottom: '1px solid rgba(255,255,255,0.1)',
        boxShadow: 'inset 0 0 20px rgba(0,0,0,0.5)',
      }}
    >
      <div
        className="hp-details-grid"
        style={{
          display: 'grid',
          gridTemplateColumns: '2fr 1fr',
          gap: '20px',
        }}
      >
        {/* Left Column: Technical Evidence */}
        <div className="hp-detail-col">
          {/* Technical Evidence Header */}
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
            <Code size={14} />
            <span>Technical Evidence</span>
          </div>

          {/* Payload Box */}
          <div
            className="hp-payload-box"
            style={{
              background: '#09090b',
              borderRadius: '6px',
              border: '1px solid #333',
              boxShadow: '0 4px 12px rgba(0,0,0,0.5)',
              overflow: 'hidden',
              fontFamily: 'Menlo, Monaco, Consolas, "Courier New", monospace',
            }}
          >
            {/* Payload Header */}
            <div
              className="hp-payload-header"
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                padding: '8px 12px',
                background: '#18181b',
                borderBottom: '1px solid #333',
                fontSize: '11px',
                color: '#a1a1aa',
              }}
            >
              <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
                {/* macOS-style dots */}
                <div
                  style={{
                    width: '10px',
                    height: '10px',
                    borderRadius: '50%',
                    background: '#ff5f56',
                  }}
                />
                <div
                  style={{
                    width: '10px',
                    height: '10px',
                    borderRadius: '50%',
                    background: '#ffbd2e',
                  }}
                />
                <div
                  style={{
                    width: '10px',
                    height: '10px',
                    borderRadius: '50%',
                    background: '#27c93f',
                  }}
                />
                <span className="hp-overline" style={{ marginLeft: '8px', opacity: 0.8 }}>
                  Captured Payload
                </span>
              </div>
              {hasPayload && <CopyButton text={payloadPre} />}
            </div>

            {/* Payload Content */}
            <div
              className="hp-payload-content"
              style={{
                padding: '16px',
                fontSize: '13px',
                color: '#26de81',
                background: '#09090b',
                whiteSpace: 'pre-wrap',
                wordBreak: 'break-all',
                lineHeight: '1.5',
              }}
            >
              {hasPayload ? (
                <>
                  {event.command && (
                    <span style={{ color: '#ff3366', marginRight: '6px' }}>$ </span>
                  )}
                  {payloadPre}
                </>
              ) : (
                <span style={{ color: '#555', fontStyle: 'italic' }}>No payload data captured</span>
              )}
            </div>
          </div>

          {/* CVEs Section */}
          <div
            className="hp-detail-header"
            style={{
              marginTop: '16px',
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
            <ShieldAlert size={14} />
            <span>Related CVEs</span>
          </div>
          <div className="hp-tags-list" style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
            {!event.matched_cves?.length && (
              <span style={{ fontSize: '12px', color: '#555' }}>No related CVEs found</span>
            )}
            {event.matched_cves?.map((cve) => (
              <a
                key={cve}
                href={`https://nvd.nist.gov/vuln/detail/${cve}`}
                target="_blank"
                rel="noopener noreferrer"
                style={{
                  padding: '2px 8px',
                  borderRadius: '4px',
                  fontSize: '11px',
                  border: '1px solid #f59e0b',
                  color: '#f59e0b',
                  background: 'rgba(245, 158, 11, 0.1)',
                  textDecoration: 'none',
                  cursor: 'pointer',
                }}
                onClick={(e) => e.stopPropagation()}
              >
                {cve}
              </a>
            ))}
          </div>

          {/* Patterns Section */}
          <div
            className="hp-detail-header"
            style={{
              marginTop: '16px',
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
            <Hash size={14} />
            <span>Matching Patterns</span>
          </div>
          <div className="hp-tags-list" style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
            {!event.detected_patterns?.length && (
              <span style={{ fontSize: '12px', color: '#555' }}>No specific patterns detected</span>
            )}
            {event.detected_patterns?.map((p, i) => (
              <span
                key={i}
                style={{
                  padding: '2px 8px',
                  borderRadius: '4px',
                  fontSize: '11px',
                  background: 'rgba(255, 255, 255, 0.1)',
                  color: '#ccc',
                }}
              >
                {p}
              </span>
            ))}
          </div>

          {/* Actions */}
          <div style={{ marginTop: '20px' }}>
            <button
              onClick={(e) => {
                e.stopPropagation();
                onSelectAttack(event);
              }}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                padding: '8px 16px',
                background: 'rgba(0, 180, 216, 0.15)',
                border: '1px solid rgba(0, 180, 216, 0.3)',
                color: '#00b4d8',
                borderRadius: '6px',
                cursor: 'pointer',
                fontSize: '12px',
                fontWeight: 600,
              }}
            >
              <ExternalLink size={14} />
              Full Analysis Details
            </button>
          </div>
        </div>

        {/* Right Column: Metadata */}
        <ThreatMetadata event={event} />
      </div>
    </div>
  );
}
