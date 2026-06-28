/**
 * Sessions Tab Component
 *
 * Displays active sessions across all users.
 */

import { RefreshCw, Key, User, Clock, Eye, Search } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import type { TFunction } from 'i18next';
import { useSessions } from '../../hooks';
import { DetailModal } from '../modals';
import PageHeader from '../shared/PageHeader';
import { Session } from '../../types';
import { useMemo, useState } from 'react';

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
  const [query, setQuery] = useState('');

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return sessions;
    return sessions.filter((s) => (s.user_email || '').toLowerCase().includes(q));
  }, [sessions, query]);

  return (
    <div className="sessions-tab">
      <PageHeader
        icon={<Key size={22} />}
        title={t('sessions.title')}
        subtitle={t('sessions.subtitle')}
        countLabel={t('sessions.countActive', { count: total })}
        actions={
          <>
            <div className="admin-search">
              <Search size={15} />
              <input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder={t('sessions.searchPlaceholder')}
                aria-label={t('sessions.searchPlaceholder')}
              />
            </div>
            <button
              className="admin-btn admin-btn-ghost admin-btn-icon"
              onClick={() => refresh()}
              title={t('common.refresh')}
            >
              <RefreshCw size={16} />
            </button>
          </>
        }
      />

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
        ) : filtered.length === 0 ? (
          <div className="admin-empty">
            <div className="admin-empty-icon">
              <Key size={48} />
            </div>
            <p className="admin-empty-title">
              {query ? t('sessions.noMatches') : t('sessions.empty')}
            </p>
            {!query && <p className="admin-empty-text">{t('sessions.emptyHint')}</p>}
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
              {filtered.map((session) => (
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

        .session-user {
          display: flex;
          align-items: center;
          gap: 0.5rem;
          font-weight: 500;
        }

        .session-id {
          font-family: var(--admin-font-mono, 'SF Mono', 'Fira Code', monospace);
          font-size: 0.8125rem;
          color: var(--admin-text-muted);
          background: var(--admin-surface-2);
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
