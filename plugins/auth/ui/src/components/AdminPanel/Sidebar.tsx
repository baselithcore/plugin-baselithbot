/**
 * Console navigation rail — a dark, grouped sidebar (the enterprise-admin
 * structural signature). Persistent and collapsible on desktop; an off-canvas
 * drawer on mobile.
 */

import { useTranslation } from 'react-i18next';
import { PanelLeftClose, PanelLeftOpen } from 'lucide-react';
import AuthLogo from '../ui/AuthLogo';
import { NAV_GROUPS } from './nav';
import type { TabType } from '../../types';

interface SidebarProps {
  activeTab: TabType;
  onSelect: (tab: TabType) => void;
  collapsed: boolean;
  onToggleCollapse: () => void;
  mobileOpen: boolean;
  onCloseMobile: () => void;
}

const Sidebar = ({
  activeTab,
  onSelect,
  collapsed,
  onToggleCollapse,
  mobileOpen,
  onCloseMobile,
}: SidebarProps) => {
  const { t } = useTranslation();

  const choose = (tab: TabType) => {
    onSelect(tab);
    onCloseMobile();
  };

  return (
    <>
      <div
        className={`sb-scrim ${mobileOpen ? 'open' : ''}`}
        onClick={onCloseMobile}
        aria-hidden="true"
      />
      <aside
        className={`sb ${collapsed ? 'is-collapsed' : ''} ${mobileOpen ? 'is-mobile-open' : ''}`}
      >
        <div className="sb-brand">
          <AuthLogo size={26} />
          <span className="sb-brand-text">
            {t('nav.adminPanel')}
            <span className="sb-brand-dot">.</span>
          </span>
        </div>

        <nav className="sb-nav" aria-label={t('nav.adminPanel')}>
          {NAV_GROUPS.map((group) => (
            <div className="sb-group" key={group.id}>
              <p className="sb-group-label">{t(group.labelKey)}</p>
              {group.items.map((item) => {
                const Icon = item.icon;
                const active = activeTab === item.id;
                return (
                  <button
                    key={item.id}
                    type="button"
                    className={`sb-item ${active ? 'active' : ''}`}
                    onClick={() => choose(item.id)}
                    aria-current={active ? 'page' : undefined}
                    title={collapsed ? t(item.labelKey) : undefined}
                  >
                    <Icon size={17} className="sb-item-ico" aria-hidden="true" />
                    <span className="sb-item-label">{t(item.labelKey)}</span>
                  </button>
                );
              })}
            </div>
          ))}
        </nav>

        <button
          type="button"
          className="sb-collapse"
          onClick={onToggleCollapse}
          title={t(collapsed ? 'nav.expand' : 'nav.collapse')}
          aria-label={t(collapsed ? 'nav.expand' : 'nav.collapse')}
        >
          {collapsed ? <PanelLeftOpen size={16} /> : <PanelLeftClose size={16} />}
          <span className="sb-item-label">{t('nav.collapse')}</span>
        </button>
      </aside>
    </>
  );
};

export default Sidebar;
