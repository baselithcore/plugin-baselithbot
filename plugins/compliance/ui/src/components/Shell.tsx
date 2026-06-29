import type { ReactNode } from 'react';
import { useTranslation } from 'react-i18next';
import { useAuth } from '@auth';

import { setLanguage } from '../i18n';
import { useUI } from '../store/useUI';
import type { TabId } from '../types';

const TABS: { id: TabId; key: string }[] = [
  { id: 'incidents', key: 'tab.incidents' },
  { id: 'dora', key: 'tab.dora' },
  { id: 'dsr', key: 'tab.dsr' },
  { id: 'thirdparty', key: 'tab.thirdparty' },
  { id: 'transparency', key: 'tab.transparency' },
];

export function Shell({ children }: { children: ReactNode }) {
  const { t, i18n } = useTranslation();
  const { tab, setTab } = useUI();
  const { user, logout, canAccessTab } = useAuth();

  return (
    <div className="shell">
      <header className="topbar">
        <div className="brand">
          <span className="brand-mark">✦</span>
          <div>
            <strong>{t('app.title')}</strong>
            <small>{t('app.subtitle')}</small>
          </div>
        </div>
        <div className="topbar-right">
          <div className="lang">
            {(['en', 'it'] as const).map((lng) => (
              <button
                key={lng}
                className={i18n.language.startsWith(lng) ? 'lang-on' : ''}
                onClick={() => setLanguage(lng)}
              >
                {lng.toUpperCase()}
              </button>
            ))}
          </div>
          {user && <span className="user">{user.email}</span>}
          <button className="btn btn-ghost" onClick={() => void logout()}>
            {t('action.logout')}
          </button>
        </div>
      </header>

      <nav className="tabs">
        {TABS.filter((x) => canAccessTab(x.id, 'compliance')).map((x) => (
          <button
            key={x.id}
            className={tab === x.id ? 'tab tab-on' : 'tab'}
            onClick={() => setTab(x.id)}
          >
            {t(x.key)}
          </button>
        ))}
      </nav>

      <main className="content">{children}</main>
    </div>
  );
}
