import { useTranslation } from 'react-i18next';
import { useAuth } from '@auth';

import { setLanguage } from '../i18n';
import { useTheme } from '../theme';
import { useUI } from '../store/useUI';
import { NAV } from './nav';

export function Topbar() {
  const { t, i18n } = useTranslation();
  const { tab, toggleSidebar } = useUI();
  const { resolved, toggle } = useTheme();
  const { user, logout } = useAuth();

  const current = NAV.flatMap((g) => g.items).find((i) => i.id === tab);

  return (
    <header className="topbar">
      <div className="crumb">
        <button className="icon-btn" onClick={toggleSidebar} aria-label="Menu">
          ☰
        </button>
        <span className="root">{t('app.title')}</span>
        <span className="sep">/</span>
        <span className="here">{current ? t(current.key) : ''}</span>
      </div>
      <div className="topbar-right">
        <button
          className="icon-btn"
          onClick={toggle}
          aria-label={t('action.theme')}
          title={t('action.theme')}
        >
          {resolved === 'dark' ? '☀' : '☾'}
        </button>
        <div className="lang">
          {(['en', 'it'] as const).map((lng) => (
            <button
              key={lng}
              className={i18n.language.startsWith(lng) ? 'on' : ''}
              onClick={() => setLanguage(lng)}
            >
              {lng.toUpperCase()}
            </button>
          ))}
        </div>
        {user && (
          <div className="user-chip">
            <b>{user.email}</b>
            <small>{t('role.admin')}</small>
          </div>
        )}
        <button className="btn btn-ghost btn-sm" onClick={() => void logout()}>
          {t('action.logout')}
        </button>
      </div>
    </header>
  );
}
