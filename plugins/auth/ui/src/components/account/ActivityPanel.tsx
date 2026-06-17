/** Security activity tab: recent login / security events with risk scoring. */

import { useEffect, useState } from 'react';
import { CheckCircle2, XCircle } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../../hooks/useAuthContext';
import { getActivity, type ActivityEntry } from '../../api/account';

function riskClass(score: number): string {
  if (score >= 70) return 'acct-risk-high';
  if (score >= 40) return 'acct-risk-med';
  return 'acct-risk-low';
}

export default function ActivityPanel() {
  const { t } = useTranslation();
  const { accessToken } = useAuth();
  const [rows, setRows] = useState<ActivityEntry[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!accessToken) return;
    getActivity(accessToken)
      .then(setRows)
      .catch(() => setRows([]))
      .finally(() => setLoading(false));
  }, [accessToken]);

  return (
    <section className="acct-card">
      <h2 className="acct-card-title">{t('account.tabs.activity')}</h2>
      <p className="acct-hint">{t('account.activity.desc')}</p>
      {loading ? (
        <p className="acct-empty">{t('account.loading')}</p>
      ) : rows.length === 0 ? (
        <p className="acct-empty">{t('account.activity.none')}</p>
      ) : (
        <div className="acct-table-wrap">
          <table className="acct-table">
            <thead>
              <tr>
                <th>{t('account.activity.event')}</th>
                <th>{t('account.activity.method')}</th>
                <th>{t('account.activity.ip')}</th>
                <th>{t('account.activity.risk')}</th>
                <th>{t('account.activity.when')}</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r, i) => (
                <tr key={i}>
                  <td>
                    {r.success ? (
                      <CheckCircle2 size={14} className="acct-ok-icon" />
                    ) : (
                      <XCircle size={14} className="acct-err-icon" />
                    )}
                    {t(`account.activity.events.${r.event}`, r.event)}
                  </td>
                  <td>{r.method}</td>
                  <td className="acct-mono">{r.ip_address || '—'}</td>
                  <td>
                    <span className={`acct-risk ${riskClass(r.risk_score)}`}>{r.risk_score}</span>
                  </td>
                  <td>{r.created_at ? new Date(r.created_at).toLocaleString() : '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
