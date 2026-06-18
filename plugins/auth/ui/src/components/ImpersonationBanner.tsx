/**
 * Impersonation Banner
 *
 * Persistent, high-visibility bar shown whenever the current session is an
 * administrator acting as another user. Makes the impersonated state obvious
 * (a key safety requirement) and offers a one-click "Stop" that restores the
 * administrator.
 */

import { useState } from 'react';
import { UserCog, LogOut } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../index';

const ImpersonationBanner = () => {
  const { t } = useTranslation();
  const { isImpersonating, impersonator, user, stopImpersonation } = useAuth();
  const [stopping, setStopping] = useState(false);

  if (!isImpersonating) return null;

  const handleStop = async () => {
    setStopping(true);
    try {
      await stopImpersonation();
      // Return to the admin console once the administrator is restored.
      window.location.href = '/auth/';
    } catch {
      setStopping(false);
    }
  };

  const targetLabel = user?.email ?? user?.username ?? user?.id ?? '';
  const adminLabel = impersonator?.email ?? impersonator?.id ?? '';

  return (
    <div className="impersonation-banner" role="alert">
      <div className="impersonation-banner-msg">
        <UserCog size={18} aria-hidden />
        <span>{t('impersonation.banner', { target: targetLabel, admin: adminLabel })}</span>
      </div>
      <button
        type="button"
        className="impersonation-banner-stop"
        onClick={handleStop}
        disabled={stopping}
      >
        <LogOut size={15} aria-hidden />
        {stopping ? t('impersonation.stopping') : t('impersonation.stop')}
      </button>

      <style>{`
        .impersonation-banner {
          position: sticky;
          top: 0;
          z-index: 1000;
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 1rem;
          flex-wrap: wrap;
          padding: 0.6rem 1rem;
          background: #b45309;
          color: #fff;
          font-size: 0.875rem;
          font-weight: 600;
          box-shadow: 0 2px 8px rgba(0, 0, 0, 0.25);
        }
        .impersonation-banner-msg {
          display: inline-flex;
          align-items: center;
          gap: 0.5rem;
        }
        .impersonation-banner-stop {
          display: inline-flex;
          align-items: center;
          gap: 0.4rem;
          padding: 0.35rem 0.8rem;
          font-size: 0.8125rem;
          font-weight: 600;
          color: #b45309;
          background: #fff;
          border: none;
          border-radius: 6px;
          cursor: pointer;
          transition: opacity 0.15s ease;
        }
        .impersonation-banner-stop:hover:not(:disabled) {
          opacity: 0.85;
        }
        .impersonation-banner-stop:disabled {
          opacity: 0.6;
          cursor: default;
        }
      `}</style>
    </div>
  );
};

export default ImpersonationBanner;
