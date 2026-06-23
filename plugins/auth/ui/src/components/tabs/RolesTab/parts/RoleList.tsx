/** Sidebar list of roles (system + custom). Presentational. */

import { useTranslation } from 'react-i18next';
import type { RbacRole } from '../../../../types';

interface Props {
  roles: RbacRole[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}

const RoleList = ({ roles, selectedId, onSelect }: Props) => {
  const { t } = useTranslation();
  return (
    <div className="roles-list">
      {roles.map((role) => {
        const active = selectedId === role.id;
        const wildcard = role.permissions.includes('*');
        return (
          <button
            key={role.id}
            className={`role-item ${active ? 'active' : ''}`}
            onClick={() => onSelect(role.id)}
          >
            <div className="role-item-main">
              <span className="role-item-name">{role.name}</span>
              <span className={`role-badge ${role.is_system ? 'sys' : 'custom'}`}>
                {role.is_system ? t('roles.system') : t('roles.custom')}
              </span>
            </div>
            <span className="role-item-meta">
              {wildcard
                ? t('roles.wildcardNote')
                : t('roles.permissionsCount', {
                    count: role.permissions.filter((p) => !p.startsWith('tab:')).length,
                  })}
            </span>
          </button>
        );
      })}
      {roles.length === 0 && <p className="admin-empty-text">{t('roles.empty')}</p>}
    </div>
  );
};

export default RoleList;
