/**
 * One discovered plugin tab: a segmented Open/Restricted policy control and,
 * when restricted, inline per-role access chips. Replaces the old sparse
 * checkbox matrix with a focused, readable row.
 */

import { Check, Lock, ShieldCheck, Unlock } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import type { RbacRole, TabPolicy } from '../../../../types';
import { tabSlug } from '../helpers';

interface Props {
  tab: TabPolicy;
  grantableRoles: RbacRole[];
  hasWildcardRole: boolean;
  onSetRestricted: (restricted: boolean) => void;
  onToggleRole: (role: RbacRole, slug: string, granted: boolean) => void;
}

const TabRow = ({ tab, grantableRoles, hasWildcardRole, onSetRestricted, onToggleRole }: Props) => {
  const { t } = useTranslation();
  const slug = tabSlug(tab.plugin, tab.tab_id);

  return (
    <div className="tabrow">
      <div className="tabrow-main">
        <div className="tabrow-id">
          <span className="tabrow-label">{tab.label}</span>
          <code className="tabrow-slug">{slug}</code>
        </div>

        <div className="seg" role="group" aria-label={t('access.columns.policy')}>
          <button
            type="button"
            className={`open ${tab.restricted ? '' : 'on'}`}
            onClick={() => onSetRestricted(false)}
            title={t('access.openHint')}
          >
            <Unlock size={13} /> {t('access.open')}
          </button>
          <button
            type="button"
            className={`restricted ${tab.restricted ? 'on' : ''}`}
            onClick={() => onSetRestricted(true)}
            title={t('access.restrictedHint')}
          >
            <Lock size={13} /> {t('access.restricted')}
          </button>
        </div>
      </div>

      {tab.restricted && (
        <div className="tabrow-roles">
          <span className="tabrow-roles-label">{t('access.columns.roles')}</span>
          {hasWildcardRole && (
            <span className="role-chip admin" title={t('access.adminAlways')}>
              <ShieldCheck size={12} /> {t('access.adminChip')}
            </span>
          )}
          {grantableRoles.map((role) => {
            const granted = role.permissions.includes(slug);
            return (
              <button
                key={role.id}
                type="button"
                className={`role-chip ${granted ? 'on' : ''}`}
                aria-pressed={granted}
                onClick={() => onToggleRole(role, slug, !granted)}
              >
                {granted && <Check size={12} />} {role.name}
              </button>
            );
          })}
          {grantableRoles.length === 0 && (
            <span className="tabrow-roles-empty">{t('access.noRoles')}</span>
          )}
        </div>
      )}
    </div>
  );
};

export default TabRow;
