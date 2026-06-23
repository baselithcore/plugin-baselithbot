/**
 * Access Control tab — the central per-plugin-tab permission matrix, redesigned
 * as grouped plugin sections with a segmented Open/Restricted control and inline
 * per-role access chips (shown only when a tab is restricted). Wildcard roles
 * (admin) always have access. Backend semantics are unchanged.
 */

import { useEffect, useMemo, useState } from 'react';
import { Lock, RefreshCw, Search } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { useRbac } from '../../../hooks/useRbac';
import { getMfaPolicy, setMfaPolicy } from '../../../api/security';
import { groupByPlugin, matchesQuery } from './helpers';
import { ACCESS_STYLES } from './styles';
import MfaPolicyCard from './parts/MfaPolicyCard';
import PluginGroup from './parts/PluginGroup';

const AccessTab = () => {
  const { t } = useTranslation();
  const { roles, tabs, loading, error, refreshTabs, toggleRestricted, togglePermission } =
    useRbac();

  const [query, setQuery] = useState('');
  const [mfaAll, setMfaAll] = useState(false);
  const [mfaSaving, setMfaSaving] = useState(false);

  useEffect(() => {
    getMfaPolicy()
      .then((p) => setMfaAll(p.mfa_required_all))
      .catch(() => {});
  }, []);

  const toggleMfaAll = async () => {
    const next = !mfaAll;
    setMfaSaving(true);
    setMfaAll(next); // optimistic
    try {
      await setMfaPolicy(next);
    } catch {
      setMfaAll(!next); // revert on failure
    } finally {
      setMfaSaving(false);
    }
  };

  const grantableRoles = useMemo(() => roles.filter((r) => !r.permissions.includes('*')), [roles]);
  const hasWildcardRole = useMemo(() => roles.some((r) => r.permissions.includes('*')), [roles]);

  const groups = useMemo(() => {
    const filtered = tabs.filter((tab) => matchesQuery(tab, tab.plugin, query));
    return groupByPlugin(filtered);
  }, [tabs, query]);

  return (
    <div className="access-tab">
      <div className="access-head">
        <div className="access-headings">
          <div className="access-title">
            <Lock size={22} />
            <h2>{t('access.title')}</h2>
          </div>
          <p className="access-desc">{t('access.description')}</p>
        </div>
        <div className="access-tools">
          <div className="access-search">
            <Search size={15} />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder={t('access.searchPlaceholder')}
              aria-label={t('access.searchPlaceholder')}
            />
          </div>
          <button className="admin-btn admin-btn-ghost" onClick={() => refreshTabs()}>
            <RefreshCw size={16} /> {t('access.refreshTabs')}
          </button>
        </div>
      </div>

      {error && <div className="admin-alert admin-alert-error">{error}</div>}

      <MfaPolicyCard value={mfaAll} saving={mfaSaving} onToggle={toggleMfaAll} />

      {loading ? (
        <div className="admin-empty">
          <div className="admin-spinner admin-spinner-lg" />
          <p className="admin-empty-text">{t('common.loading')}</p>
        </div>
      ) : groups.length === 0 ? (
        <div className="admin-card access-empty">
          {query ? t('access.noMatches') : t('access.empty')}
        </div>
      ) : (
        <div className="access-groups">
          {groups.map((group) => (
            <PluginGroup
              key={group.plugin}
              group={group}
              grantableRoles={grantableRoles}
              hasWildcardRole={hasWildcardRole}
              onSetRestricted={toggleRestricted}
              onToggleRole={togglePermission}
            />
          ))}
        </div>
      )}

      <style>{ACCESS_STYLES}</style>
    </div>
  );
};

export default AccessTab;
