/**
 * Sessions Tab Component
 *
 * Displays active sessions across all users.
 */

import { RefreshCw, Key, User, Clock, Eye } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import type { TFunction } from 'i18next';
import { useSessions } from '../../hooks';
import { DetailModal } from '../modals';
import { Session } from '../../types';
import { useState } from 'react';

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

const getTimeRemaining = (expiresAt: string, t: TFunction): string => {
  const now = new Date();
  const expires = new Date(expiresAt);
  const diff = expires.getTime() - now.getTime();

  if (diff <= 0) return t('sessions.expired');

  const days = Math.floor(diff / (1000 * 60 * 60 * 24));
  const hours = Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
  const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));

  if (days > 0) return `${days}d ${hours}h`;
  if (hours > 0) return `${hours}h ${minutes}m`;
  return `${minutes}m`;
};

const SessionsTab = () => {
  const { t } = useTranslation();
  const { sessions, total, isLoading, error, refresh } = useSessions();
  const [selectedSession, setSelectedSession] = useState<Session | null>(null);

  return (
    <div className="sessions-tab">
      {/* Header */}
      <div className="sessions-header">
        <div className="sessions-title">
          <Key size={20} />
          <h2>{t('sessions.title')}</h2>
          <span className="sessions-count">{t('sessions.countActive', { count: total })}</span>
        </div>

        <button
          className="admin-btn admin-btn-ghost admin-btn-icon"
          onClick={() => refresh()}
          title={t('common.refresh')}
        >
          <RefreshCw size={16} />
        </button>
      </div>

      {/* Error display */}
      {error && (
        <div className="admin-alert admin-alert-error">
          <span>{t('common.errorLabel', { message: error })}</span>
        </div>
      )}

      {/* Sessions Table */}
      <div className="admin-card">
        {isLoading ? (
          <div className="admin-empty">
            <div className="admin-spinner admin-spinner-lg" />
            <p className="admin-empty-text">{t('sessions.loading')}</p>
          </div>
        ) : sessions.length === 0 ? (
          <div className="admin-empty">
            <div className="admin-empty-icon">
              <Key size={48} />
            </div>
            <p className="admin-empty-title">{t('sessions.empty')}</p>
            <p className="admin-empty-text">{t('sessions.emptyHint')}</p>
          </div>
        ) : (
          <table className="admin-table">
            <thead>
              <tr>
                <th>{t('sessions.columns.user')}</th>
                <th>{t('sessions.columns.sessionId')}</th>
                <th>{t('sessions.columns.created')}</th>
                <th>{t('sessions.columns.expires')}</th>
                <th>{t('sessions.columns.timeRemaining')}</th>
                <th>{t('sessions.columns.actions')}</th>
              </tr>
            </thead>
            <tbody>
              {sessions.map((session) => (
                <tr key={session.id}>
                  <td>
                    <div className="session-user">
                      <User size={14} />
                      <span>{session.user_email}</span>
                    </div>
                  </td>
                  <td>
                    <code className="session-id">{session.id.slice(0, 8)}...</code>
                  </td>
                  <td>
                    <span className="session-date">{formatDate(session.created_at)}</span>
                  </td>
                  <td>
                    <span className="session-date">{formatDate(session.expires_at)}</span>
                  </td>
                  <td>
                    <div className="session-time-remaining">
                      <Clock size={14} />
                      <span>{getTimeRemaining(session.expires_at, t)}</span>
                    </div>
                  </td>
                  <td>
                    <button
                      className="admin-btn admin-btn-ghost admin-btn-icon"
                      onClick={() => setSelectedSession(session)}
                      title={t('sessions.viewDetails')}
                    >
                      <Eye size={16} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <DetailModal
        isOpen={!!selectedSession}
        onClose={() => setSelectedSession(null)}
        title={t('sessions.detailTitle')}
        data={
          selectedSession
            ? {
                ...selectedSession,
                time_remaining: getTimeRemaining(selectedSession.expires_at, t),
              }
            : null
        }
        formatters={{
          created_at: (val) => formatDate(val),
          expires_at: (val) => formatDate(val),
        }}
      />

      <style>{`
        .sessions-tab {
          display: flex;
          flex-direction: column;
          gap: 1.25rem;
        }

        .sessions-header {
          display: flex;
          align-items: center;
          justify-content: space-between;
        }

        .sessions-title {
          display: flex;
          align-items: center;
          gap: 0.75rem;
          color: var(--admin-text);
        }

        .sessions-title h2 {
          margin: 0;
        }

        .sessions-count {
          padding: 0.25rem 0.625rem;
          font-size: 0.75rem;
          font-weight: 500;
          color: var(--admin-accent);
          background: hsla(200, 80%, 50%, 0.15);
          border-radius: 9999px;
        }

        .session-user {
          display: flex;
          align-items: center;
          gap: 0.5rem;
          font-weight: 500;
        }

        .session-id {
          font-family: 'SF Mono', 'Fira Code', 'Consolas', monospace;
          font-size: 0.8125rem;
          color: var(--admin-text-muted);
          background: hsla(220, 25%, 20%, 0.5);
          padding: 0.125rem 0.375rem;
          border-radius: 0.25rem;
        }

        .session-date {
          font-size: 0.8125rem;
          color: var(--admin-text-muted);
        }

        .session-time-remaining {
          display: flex;
          align-items: center;
          gap: 0.375rem;
          font-size: 0.8125rem;
          color: var(--admin-success);
        }
      `}</style>
    </div>
  );
};

export default SessionsTab;
