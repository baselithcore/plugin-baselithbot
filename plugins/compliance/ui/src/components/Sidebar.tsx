import { useTranslation } from 'react-i18next';
import { useAuth } from '@auth';

import { useUI } from '../store/useUI';
import { NAV } from './nav';

export function Sidebar({ overdue }: { overdue: number }) {
  const { t } = useTranslation();
  const { tab, setTab, sidebarOpen } = useUI();
  const { canAccessTab } = useAuth();

  return (
    <nav className={`sb${sidebarOpen ? ' open' : ''}`} aria-label="Compliance navigation">
      <div className="sb-brand">
        <span className="sb-brand-mark">✓</span>
        <span className="sb-brand-text">
          {t('app.title')}
          <small>{t('app.subtitle')}</small>
        </span>
      </div>
      <div className="sb-nav">
        {NAV.map((group) => {
          const items = group.items.filter((i) => canAccessTab(i.id, 'compliance'));
          if (items.length === 0) return null;
          return (
            <div className="sb-group" key={group.labelKey}>
              <p className="sb-group-label">{t(group.labelKey)}</p>
              {items.map((item) => (
                <button
                  key={item.id}
                  className={`sb-item${tab === item.id ? ' on' : ''}`}
                  onClick={() => setTab(item.id)}
                >
                  <span className="ico">{item.icon}</span>
                  <span>{t(item.key)}</span>
                  {item.id === 'overview' && overdue > 0 && <span className="pill">{overdue}</span>}
                </button>
              ))}
            </div>
          );
        })}
      </div>
    </nav>
  );
}
