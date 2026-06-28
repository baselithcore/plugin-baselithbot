/**
 * Security-posture panel — the at-a-glance health an identity admin actually
 * monitors: MFA coverage, locked accounts, inactive accounts, live sessions.
 * Replaces the generic donut with status-encoded rows.
 */

import { useTranslation } from 'react-i18next';
import { Meter } from './charts';
import type { OverviewData } from './hooks';

const MFA_TARGET = 80;

const Posture = ({ data }: { data: OverviewData }) => {
  const { t } = useTranslation();
  const inactive = Math.max(0, data.totalUsers - data.activeUsers);
  const mfaTone = data.mfa.pct >= MFA_TARGET ? 'success' : data.mfa.pct >= 50 ? 'accent' : 'warning';

  return (
    <section className="admin-card ov-card">
      <header className="ov-card-head">
        <h3>{t('overview.posture.title')}</h3>
      </header>
      <ul className="ov-posture">
        <li>
          <span className="ov-posture-label">{t('overview.posture.mfa')}</span>
          <span className="ov-posture-meter">
            <Meter pct={data.mfa.pct} tone={mfaTone} />
          </span>
          <span className="ov-posture-val">{data.mfa.pct}%</span>
        </li>
        <li>
          <span className="ov-posture-label">
            <i className={`ov-dot ${data.withoutMfa ? 'warn' : 'ok'}`} aria-hidden="true" />
            {t('overview.posture.withoutMfa')}
          </span>
          <span className="ov-posture-val">{data.withoutMfa}</span>
        </li>
        <li>
          <span className="ov-posture-label">
            <i className={`ov-dot ${data.lockedUsers ? 'bad' : 'ok'}`} aria-hidden="true" />
            {t('overview.posture.locked')}
          </span>
          <span className="ov-posture-val">{data.lockedUsers}</span>
        </li>
        <li>
          <span className="ov-posture-label">
            <i className={`ov-dot ${inactive ? 'warn' : 'ok'}`} aria-hidden="true" />
            {t('overview.posture.inactive')}
          </span>
          <span className="ov-posture-val">{inactive}</span>
        </li>
        <li>
          <span className="ov-posture-label">
            <i className={`ov-dot ${data.failedLogins ? 'warn' : 'ok'}`} aria-hidden="true" />
            {t('overview.posture.failed')}
          </span>
          <span className="ov-posture-val">{data.failedLogins}</span>
        </li>
      </ul>
    </section>
  );
};

export default Posture;
