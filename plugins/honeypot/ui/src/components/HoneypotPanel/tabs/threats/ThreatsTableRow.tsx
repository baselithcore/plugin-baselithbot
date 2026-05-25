/**
 * ThreatsTableRow - Individual table row component
 * Handles row display and expansion of threat details
 */

import { ChevronDown, ChevronUp } from 'lucide-react';
import { AttackEvent } from '../../../types';
import { normalizeIpDisplay } from '../../../api';
import { getSeverityClass, getProtocolIcon } from '../../utils';
import { getCountryFlag } from '../../../geoUtils';
import BotIndicator from '../../../common/BotIndicator';
import { ThreatDetailsPanel } from './ThreatDetailsPanel';

interface ThreatsTableRowProps {
  event: AttackEvent;
  isExpanded: boolean;
  onToggle: () => void;
  onSelectAttack: (event: AttackEvent) => void;
}

export function ThreatsTableRow({
  event,
  isExpanded,
  onToggle,
  onSelectAttack,
}: ThreatsTableRowProps) {
  return (
    <>
      {/* Main Row */}
      <tr
        onClick={onToggle}
        className={`hp-event-row ${isExpanded ? 'expanded' : ''} ${getSeverityClass(event.severity)}`}
        style={{
          cursor: 'pointer',
          background: isExpanded ? 'rgba(255, 255, 255, 0.05)' : undefined,
        }}
      >
        {/* Severity Stripe */}
        <td className="hp-col-severity">
          <span
            className={`hp-severity-stripe ${event.severity}`}
            style={{
              display: 'block',
              width: '4px',
              height: '24px',
              borderRadius: '2px',
              background: `var(--cyber-${event.severity})`,
            }}
          />
        </td>

        {/* Timestamp */}
        <td className="hp-timestamp">{new Date(event.timestamp).toLocaleString()}</td>

        {/* Source IP */}
        <td className="hp-source-ip">{normalizeIpDisplay(event.source_ip)}</td>

        {/* Location */}
        <td className="hp-location">
          <span className="hp-flag">{getCountryFlag(event.geo?.country_code || undefined)}</span>
          <span className="hp-country-name">{event.geo?.country || 'Unknown'}</span>
        </td>

        {/* Honeypot */}
        <td className="hp-honeypot">{event.honeypot_id}</td>

        {/* Protocol */}
        <td className="hp-protocol">
          <span className="hp-proto-badge">
            {getProtocolIcon(event.protocol)} {event.protocol.toUpperCase()}
          </span>
        </td>

        {/* Category */}
        <td className="hp-category">{event.category}</td>

        {/* Severity */}
        <td className="hp-severity">
          <span className={`hp-severity-tag ${event.severity}`}>
            {event.severity.toUpperCase()}
          </span>
        </td>

        {/* Bot/Human Indicator */}
        <td className="hp-bot">
          <BotIndicator
            isBot={event.is_bot}
            confidence={event.bot_confidence}
            size="small"
            showLabel={false}
          />
        </td>

        {/* Details Preview */}
        <td className="hp-details-preview">
          <div className="hp-terminal-cell">
            <span className="hp-prompt">❯</span>
            <span className="hp-command">
              {event.command || event.http_path || event.username || (
                <span className="hp-no-data">_no_data</span>
              )}
            </span>
          </div>
        </td>

        {/* Expand Icon */}
        <td style={{ textAlign: 'center', opacity: 0.5 }}>
          {isExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
        </td>
      </tr>

      {/* Expanded Details Row */}
      {isExpanded && (
        <tr className="hp-threat-details-row">
          <td colSpan={11} style={{ padding: 0, border: 'none' }}>
            <ThreatDetailsPanel event={event} onSelectAttack={onSelectAttack} />
          </td>
        </tr>
      )}
    </>
  );
}
