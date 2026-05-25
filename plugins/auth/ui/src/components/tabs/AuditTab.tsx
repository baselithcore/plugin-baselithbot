/**
 * Audit Tab Component
 *
 * Displays audit log entries with filtering and pagination.
 */

import { useState } from 'react';
import {
  RefreshCw,
  Activity,
  User,
  Clock,
  ChevronLeft,
  ChevronRight,
  Filter,
  Eye,
} from 'lucide-react';
import { useAudit } from '../../hooks';
import { DetailModal } from '../modals';
import { AuditEntry } from '../../types';

const formatDate = (dateStr: string): string => {
  const date = new Date(dateStr);
  return date.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
};

const AUDIT_ACTIONS = [
  { value: '', label: 'All Actions' },
  { value: 'user_created', label: 'User Created' },
  { value: 'user_updated', label: 'User Updated' },
  { value: 'user_deleted', label: 'User Deleted' },
  { value: 'user_password_reset', label: 'Password Reset' },
  { value: 'user_unlocked', label: 'User Unlocked' },
  { value: 'user_sessions_revoked', label: 'Sessions Revoked' },
  { value: 'user_mfa_disabled', label: 'MFA Disabled' },
  { value: 'login_success', label: 'Login Success' },
  { value: 'login_failure', label: 'Login Failure' },
  { value: 'logout', label: 'Logout' },
];

const getActionBadgeClass = (action: string): string => {
  if (action.includes('created')) return 'audit-badge-success';
  if (action.includes('deleted') || action.includes('failure')) return 'audit-badge-danger';
  if (action.includes('updated') || action.includes('reset')) return 'audit-badge-warning';
  return 'audit-badge-default';
};

const formatActionLabel = (action: string): string => {
  return action.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
};

// Helper to render detail items as pills
const renderDetailPills = (details: Record<string, unknown>) => {
  if (!details || Object.keys(details).length === 0)
    return <span className="audit-content-empty">-</span>;

  const entries = Object.entries(details);
  const displayLimit = 2; // Show max 2 items inline
  const remainder = entries.length - displayLimit;

  return (
    <div className="audit-content-pills">
      {entries.slice(0, displayLimit).map(([key, value]) => {
        let displayValue = String(value);

        // Handle Diff Objects (from/to)
        if (typeof value === 'object' && value !== null) {
          const valObj = value as Record<string, unknown>;
          if ('from' in valObj || 'to' in valObj) {
            const from = valObj.from !== undefined ? String(valObj.from) : '(empty)';
            const to = valObj.to !== undefined ? String(valObj.to) : '(empty)';
            displayValue = `${from} → ${to}`;
          } else {
            displayValue = '{...}';
          }
        }

        if (displayValue.length > 40) displayValue = displayValue.slice(0, 40) + '...';

        return (
          <span key={key} className="audit-pill">
            <span className="audit-pill-key">{key}:</span>
            <span className="audit-pill-value">{displayValue}</span>
          </span>
        );
      })}
      {remainder > 0 && <span className="audit-pill audit-pill-more">+{remainder} more</span>}
    </div>
  );
};

const AuditTab = () => {
  const { entries, total, page, limit, isLoading, error, refresh, setPage, setActionFilter } =
    useAudit();

  const [filterAction, setFilterAction] = useState('');
  const [selectedEntry, setSelectedEntry] = useState<AuditEntry | null>(null);
  const totalPages = Math.ceil(total / limit);

  const handleFilterChange = (action: string) => {
    setFilterAction(action);
    setActionFilter(action || null);
  };

  return (
    <div className="audit-tab">
      {/* Header */}
      <div className="audit-header">
        <div className="audit-title">
          <Activity size={20} />
          <h2>Audit Log</h2>
          <span className="audit-count">{total} entries</span>
        </div>

        <div className="audit-controls">
          {/* Filter dropdown */}
          <div className="audit-filter">
            <Filter size={14} />
            <select
              value={filterAction}
              onChange={(e) => handleFilterChange(e.target.value)}
              className="audit-filter-select"
            >
              {AUDIT_ACTIONS.map((action) => (
                <option key={action.value} value={action.value}>
                  {action.label}
                </option>
              ))}
            </select>
          </div>

          <button
            className="admin-btn admin-btn-ghost admin-btn-icon"
            onClick={() => refresh()}
            title="Refresh"
          >
            <RefreshCw size={16} />
          </button>
        </div>
      </div>

      {/* Error display */}
      {error && (
        <div className="admin-alert admin-alert-error">
          <span>Error: {error}</span>
        </div>
      )}

      {/* Audit Table */}
      <div className="admin-card">
        {isLoading ? (
          <div className="admin-empty">
            <div className="admin-spinner admin-spinner-lg" />
            <p className="admin-empty-text">Loading audit log...</p>
          </div>
        ) : entries.length === 0 ? (
          <div className="admin-empty">
            <div className="admin-empty-icon">
              <Activity size={48} />
            </div>
            <p className="admin-empty-title">No audit entries</p>
            <p className="admin-empty-text">
              {filterAction
                ? 'No entries match the selected filter.'
                : 'No audit log entries recorded yet.'}
            </p>
          </div>
        ) : (
          <table className="admin-table">
            <thead>
              <tr>
                <th>Timestamp</th>
                <th>Action</th>
                <th>Actor</th>
                <th>Target</th>
                <th>Content</th>
                <th>IP Address</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {entries.map((entry) => (
                <tr
                  key={entry.id}
                  onClick={() => setSelectedEntry(entry)}
                  style={{ cursor: 'pointer' }}
                >
                  <td>
                    <div className="audit-timestamp">
                      <Clock size={14} />
                      <span>{formatDate(entry.created_at)}</span>
                    </div>
                  </td>
                  <td>
                    <span className={`audit-badge ${getActionBadgeClass(entry.action)}`}>
                      {formatActionLabel(entry.action)}
                    </span>
                  </td>
                  <td>
                    <div className="audit-actor">
                      <User size={14} />
                      <code className="audit-id">{entry.actor_id.slice(0, 8)}...</code>
                    </div>
                  </td>
                  <td>
                    {entry.target_id ? (
                      <code className="audit-id">{entry.target_id.slice(0, 8)}...</code>
                    ) : (
                      <span className="audit-na">-</span>
                    )}
                  </td>
                  <td>{renderDetailPills(entry.details)}</td>
                  <td>
                    {entry.ip_address ? (
                      <code className="audit-ip">{entry.ip_address}</code>
                    ) : (
                      <span className="audit-na">-</span>
                    )}
                  </td>
                  <td>
                    <button
                      className="admin-btn admin-btn-ghost admin-btn-icon"
                      onClick={(e) => {
                        e.stopPropagation();
                        setSelectedEntry(entry);
                      }}
                      title="View Details"
                    >
                      <Eye size={16} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="audit-pagination">
            <span className="audit-pagination-info">
              Page {page} of {totalPages}
            </span>
            <div className="audit-pagination-controls">
              <button
                className="admin-btn admin-btn-ghost admin-btn-sm"
                onClick={() => setPage(page - 1)}
                disabled={page <= 1}
              >
                <ChevronLeft size={16} />
                <span>Prev</span>
              </button>
              <button
                className="admin-btn admin-btn-ghost admin-btn-sm"
                onClick={() => setPage(page + 1)}
                disabled={page >= totalPages}
              >
                <span>Next</span>
                <ChevronRight size={16} />
              </button>
            </div>
          </div>
        )}
      </div>

      <DetailModal
        isOpen={!!selectedEntry}
        onClose={() => setSelectedEntry(null)}
        title="Audit Log Details"
        data={
          selectedEntry
            ? {
                ...selectedEntry,
                details: selectedEntry.details || {}, // Ensure details is an object
              }
            : null
        }
        formatters={{
          created_at: (val) => formatDate(val),
          action: (val) => formatActionLabel(val),
        }}
      />

      <style>{`
        .audit-tab {
          display: flex;
          flex-direction: column;
          gap: 1.25rem;
        }

        .audit-header {
          display: flex;
          align-items: center;
          justify-content: space-between;
        }

        .audit-title {
          display: flex;
          align-items: center;
          gap: 0.75rem;
          color: var(--admin-text);
        }

        .audit-title h2 {
          margin: 0;
        }

        .audit-count {
          padding: 0.25rem 0.625rem;
          font-size: 0.75rem;
          font-weight: 500;
          color: var(--admin-accent);
          background: hsla(200, 80%, 50%, 0.15);
          border-radius: 9999px;
        }

        .audit-controls {
          display: flex;
          align-items: center;
          gap: 0.75rem;
        }

        .audit-filter {
          display: flex;
          align-items: center;
          gap: 0.5rem;
          padding: 0.375rem 0.75rem;
          background: var(--admin-bg-tertiary);
          border: 1px solid var(--admin-border);
          border-radius: 0.5rem;
          color: var(--admin-text-muted);
        }

        .audit-filter-select {
          background: transparent;
          border: none;
          color: var(--admin-text);
          font-size: 0.8125rem;
          cursor: pointer;
          outline: none;
        }

        .audit-filter-select option {
          background: var(--admin-bg-secondary);
          color: var(--admin-text);
        }

        .audit-timestamp {
          display: flex;
          align-items: center;
          gap: 0.375rem;
          font-size: 0.8125rem;
          color: var(--admin-text-muted);
        }

        .audit-badge {
          display: inline-flex;
          padding: 0.25rem 0.5rem;
          font-size: 0.6875rem;
          font-weight: 600;
          text-transform: uppercase;
          letter-spacing: 0.025em;
          border-radius: 0.25rem;
        }

        .audit-badge-success {
          color: var(--admin-success);
          background: hsla(145, 80%, 42%, 0.15);
        }

        .audit-badge-warning {
          color: var(--admin-warning);
          background: hsla(35, 92%, 50%, 0.15);
        }

        .audit-badge-danger {
          color: var(--admin-error);
          background: hsla(0, 80%, 55%, 0.15);
        }

        .audit-badge-default {
          color: var(--admin-text-muted);
          background: hsla(220, 25%, 50%, 0.15);
        }

        .audit-actor {
          display: flex;
          align-items: center;
          gap: 0.375rem;
        }

        .audit-id,
        .audit-ip,
        .audit-details {
          font-family: 'SF Mono', 'Fira Code', 'Consolas', monospace;
          font-size: 0.75rem;
          color: var(--admin-text-muted);
          background: hsla(220, 25%, 20%, 0.5);
          padding: 0.125rem 0.375rem;
          border-radius: 0.25rem;
        }

        .audit-na {
          color: var(--admin-text-muted);
          opacity: 0.5;
        }

        .audit-pagination {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 1rem 1.25rem;
          border-top: 1px solid var(--admin-border);
        }

        .audit-pagination-info {
          font-size: 0.8125rem;
          color: var(--admin-text-muted);
        }

        .audit-pagination-controls {
          display: flex;
          gap: 0.5rem;
        }

        .admin-btn-sm {
          padding: 0.375rem 0.75rem;
          font-size: 0.8125rem;
        }

        .admin-btn-sm svg {
          width: 14px;
          height: 14px;
        }

        .audit-content-pills {
          display: flex;
          align-items: center;
          gap: 0.5rem;
          flex-wrap: wrap;
        }

        .audit-content-empty {
          color: var(--admin-text-subtle);
          font-size: 0.8125rem;
        }

        .audit-pill {
          display: inline-flex;
          align-items: center;
          gap: 0.25rem;
          padding: 0.125rem 0.5rem;
          background: hsla(220, 25%, 20%, 0.5);
          border: 1px solid var(--admin-table-border);
          border-radius: 9999px;
          font-size: 0.75rem;
          font-family: 'SF Mono', 'Fira Code', 'Consolas', monospace;
          white-space: nowrap;
        }

        .audit-pill-key {
          color: var(--admin-text-muted);
          font-weight: 500;
        }

        .audit-pill-value {
          color: var(--admin-text);
        }

        .audit-pill-more {
          background: hsla(220, 25%, 25%, 0.8);
          color: var(--admin-text-muted);
          cursor: help;
        }
      `}</style>
    </div>
  );
};

export default AuditTab;
