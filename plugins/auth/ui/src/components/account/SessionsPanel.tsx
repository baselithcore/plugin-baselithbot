/** Sessions & devices tab: list active sessions, revoke individually or all. */

import { useCallback, useEffect, useState } from 'react';
import { MonitorSmartphone, LogOut } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../../hooks/useAuthContext';
import {
  listSessions,
  revokeSession,
  revokeOtherSessions,
  type SessionInfo,
} from '../../api/account';

export default function SessionsPanel() {
  const { t } = useTranslation();
  const { accessToken } = useAuth();
  const [sessions, setSessions] = useState<SessionInfo[]>([]);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  const load = useCallback(() => {
    if (!accessToken) return;
    setLoading(true);
    listSessions(accessToken)
      .then(setSessions)
      .catch((e) => setError(e instanceof Error ? e.message : 'Error'))
      .finally(() => setLoading(false));
  }, [accessToken]);

  useEffect(load, [load]);

  const revoke = async (id: string) => {
    if (!accessToken) return;
    try {
      await revokeSession(accessToken, id);
      load();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Error');
    }
  };

  const revokeOthers = async () => {
    if (!accessToken) return;
    try {
      await revokeOtherSessions(accessToken);
      load();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Error');
    }
  };

  return (
    <section className="acct-card">
      <div className="acct-card-head">
        <h2 className="acct-card-title">{t('account.tabs.sessions')}</h2>
        {sessions.length > 1 && (
          <button className="acct-btn acct-btn-secondary" onClick={revokeOthers}>
            <LogOut size={14} /> {t('account.sessions.revokeOthers')}
          </button>
        )}
      </div>
      {error && <div className="acct-alert acct-alert-error">{error}</div>}
      {loading ? (
        <p className="acct-empty">{t('account.loading')}</p>
      ) : sessions.length === 0 ? (
        <p className="acct-empty">{t('account.sessions.none')}</p>
      ) : (
        <ul className="acct-list">
          {sessions.map((s) => (
            <li key={s.id} className="acct-list-row">
              <div>
                <strong>
                  <MonitorSmartphone size={14} /> {t('account.sessions.session')}
                  {s.current && (
                    <span className="acct-badge acct-badge-ok">
                      {t('account.sessions.current')}
                    </span>
                  )}
                </strong>
                <span className="acct-meta">
                  {t('account.sessions.started', {
                    date: s.created_at ? new Date(s.created_at).toLocaleString() : '—',
                  })}
                </span>
              </div>
              {!s.current && (
                <button
                  className="acct-icon-btn"
                  onClick={() => revoke(s.id)}
                  aria-label={t('account.sessions.revoke')}
                >
                  <LogOut size={15} />
                </button>
              )}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
