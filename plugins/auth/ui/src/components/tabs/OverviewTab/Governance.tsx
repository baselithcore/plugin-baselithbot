/**
 * Access & onboarding panel — governance posture an identity admin tracks:
 * configured SSO providers, outstanding invitations, live sessions.
 */

import { useTranslation } from 'react-i18next';
import type { OverviewData } from './hooks';

const Governance = ({ data }: { data: OverviewData }) => {
  const { t } = useTranslation();
  return (
    <section className="admin-card ov-card">
      <header className="ov-card-head">
        <h3>{t('overview.access.title')}</h3>
      </header>
      <ul className="ov-posture">
        <li>
          <span className="ov-posture-label">{t('overview.access.sso')}</span>
          <span className="ov-posture-val">{data.ssoProviders}</span>
        </li>
        <li>
          <span className="ov-posture-label">
            <i className={`ov-dot ${data.pendingInvites ? 'warn' : 'ok'}`} aria-hidden="true" />
            {t('overview.access.invites')}
          </span>
          <span className="ov-posture-val">{data.pendingInvites}</span>
        </li>
        <li>
          <span className="ov-posture-label">{t('overview.access.sessions')}</span>
          <span className="ov-posture-val">{data.activeSessions}</span>
        </li>
      </ul>
    </section>
  );
};

export default Governance;
