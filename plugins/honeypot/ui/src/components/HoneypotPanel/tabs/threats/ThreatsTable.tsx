/**
 * ThreatsTable - Table wrapper component
 * Handles table structure, loading state, and row rendering
 */

import { AttackEvent } from '../../../types';
import { ThreatsTableRow } from './ThreatsTableRow';

interface ThreatsTableProps {
  events: AttackEvent[];
  loading: boolean;
  expandedId: string | null;
  onToggleRow: (eventId: string) => void;
  onSelectAttack: (event: AttackEvent) => void;
}

export function ThreatsTable({
  events,
  loading,
  expandedId,
  onToggleRow,
  onSelectAttack,
}: ThreatsTableProps) {
  return (
    <div className="hp-table-container">
      <table className="hp-events-table">
        <thead>
          <tr>
            <th style={{ width: '40px' }}></th> {/* Severity Stripe */}
            <th>Timestamp</th>
            <th>Source</th>
            <th>Location</th>
            <th>Honeypot</th>
            <th>Protocol</th>
            <th>Category</th>
            <th>Severity</th>
            <th>Bot/Human</th>
            <th>Details</th>
            <th style={{ width: '40px' }}></th> {/* Expand icon */}
          </tr>
        </thead>
        <tbody>
          {loading && events.length === 0 ? (
            <tr>
              <td colSpan={11} className="hp-loading-cell">
                Loading...
              </td>
            </tr>
          ) : events.length === 0 ? (
            <tr>
              <td colSpan={11} className="hp-empty-cell">
                No events found matching filters
              </td>
            </tr>
          ) : (
            events.map((event) => (
              <ThreatsTableRow
                key={event.event_id}
                event={event}
                isExpanded={expandedId === event.event_id}
                onToggle={() => onToggleRow(event.event_id)}
                onSelectAttack={onSelectAttack}
              />
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}
