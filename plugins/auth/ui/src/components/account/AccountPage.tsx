/**
 * Self-service "My Account" surface. Available to every authenticated user
 * (not admin-gated): profile, security (password / MFA / passkeys), sessions
 * & devices, security activity, and personal access tokens.
 */

import { useCallback, useEffect, useState } from 'react';
import {
  User,
  ShieldCheck,
  MonitorSmartphone,
  Activity,
  KeyRound,
  TrendingUp,
  ArrowLeft,
} from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../../hooks/useAuthContext';
import { getAccount, type Account } from '../../api/account';
import LanguageSwitcher from '../ui/LanguageSwitcher';
import AuthLogo from '../ui/AuthLogo';
import ProfilePanel from './ProfilePanel';
import SecurityPanel from './SecurityPanel';
import SessionsPanel from './SessionsPanel';
import ActivityPanel from './ActivityPanel';
import ApiKeysPanel from './ApiKeysPanel';
import UsagePanel from './UsagePanel';
import UsageOverlay from './UsageOverlay';
import './account.css';

type Tab = 'profile' | 'security' | 'sessions' | 'activity' | 'apikeys' | 'usage';

const TABS: { id: Tab; icon: typeof User; key: string }[] = [
  { id: 'profile', icon: User, key: 'account.tabs.profile' },
  { id: 'security', icon: ShieldCheck, key: 'account.tabs.security' },
  { id: 'sessions', icon: MonitorSmartphone, key: 'account.tabs.sessions' },
  { id: 'activity', icon: Activity, key: 'account.tabs.activity' },
  { id: 'apikeys', icon: KeyRound, key: 'account.tabs.apikeys' },
  { id: 'usage', icon: TrendingUp, key: 'account.tabs.usage' },
];

export default function AccountPage() {
  const { t } = useTranslation();
  const { accessToken, user, hasRole } = useAuth();
  const [tab, setTab] = useState<Tab>('profile');
  const [account, setAccount] = useState<Account | null>(null);
  const [error, setError] = useState('');

  const reload = useCallback(() => {
    if (!accessToken) return;
    getAccount(accessToken)
      .then(setAccount)
      .catch((e) => setError(e instanceof Error ? e.message : 'Error'));
  }, [accessToken]);

  useEffect(reload, [reload]);

  return (
    <div className="acct-layout">
      <UsageOverlay />
      <div className="aurora" aria-hidden="true" />
      <header className="acct-header">
        <a className="acct-brand" href="/auth/">
          <AuthLogo size={24} />
          <span>{t('account.title')}</span>
        </a>
        <div className="acct-header-right">
          <LanguageSwitcher />
          {hasRole('admin') && (
            <a className="acct-admin-link" href="/auth/">
              <ArrowLeft size={14} /> {t('account.toAdmin')}
            </a>
          )}
        </div>
      </header>

      <div className="acct-body">
        <aside className="acct-sidebar">
          <div className="acct-identity">
            <div className="acct-avatar">
              {(account?.full_name || account?.email || '?').charAt(0).toUpperCase()}
            </div>
            <div className="acct-identity-text">
              <div className="acct-name">
                {account?.full_name || account?.username || user?.email}
              </div>
              <div className="acct-email">{account?.email}</div>
            </div>
          </div>
          <nav className="acct-nav">
            {TABS.map(({ id, icon: Icon, key }) => (
              <button
                key={id}
                className={`acct-nav-item ${tab === id ? 'active' : ''}`}
                onClick={() => setTab(id)}
              >
                <Icon size={16} />
                <span>{t(key)}</span>
              </button>
            ))}
          </nav>
        </aside>

        <main className="acct-content">
          {error && <div className="acct-alert acct-alert-error">{error}</div>}
          {tab === 'profile' && <ProfilePanel account={account} onChange={reload} />}
          {tab === 'security' && <SecurityPanel account={account} onChange={reload} />}
          {tab === 'sessions' && <SessionsPanel />}
          {tab === 'activity' && <ActivityPanel />}
          {tab === 'apikeys' && <ApiKeysPanel />}
          {tab === 'usage' && <UsagePanel />}
        </main>
      </div>
    </div>
  );
}
