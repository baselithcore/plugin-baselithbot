/**
 * Permission matrix for one role: collapsible category groups, per-category
 * bulk grant/revoke, per-permission toggle with a live diff highlight, and a
 * sticky save bar that commits the staged set in one batch.
 */

import { useMemo, useState } from 'react';
import { Check, ChevronDown, ChevronRight, Save, Undo2 } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import type { RbacPermission, RbacRole } from '../../../../types';
import type { RoleEditor } from '../hooks';
import { categoryIcon, sortedCategories } from '../permission_catalog';

interface Props {
  role: RbacRole;
  permsByCategory: Record<string, RbacPermission[]>;
  editor: RoleEditor;
}

const PermissionMatrix = ({ role, permsByCategory, editor }: Props) => {
  const { t } = useTranslation();
  const [collapsed, setCollapsed] = useState<Set<string>>(new Set());
  const categories = useMemo(
    () => sortedCategories(Object.keys(permsByCategory)),
    [permsByCategory]
  );
  // Permission slugs contain dots (e.g. "users.manage"), which i18next would
  // otherwise treat as key separators — fetch the whole localized map once and
  // index it directly, falling back to the backend (English) description.
  const descMap = t('roles.permissionDescriptions', { returnObjects: true }) as unknown as Record<
    string,
    string
  >;
  const describe = (p: RbacPermission) =>
    (descMap && descMap[p.slug]) || p.description || p.slug;

  const toggleCollapse = (cat: string) =>
    setCollapsed((prev) => {
      const next = new Set(prev);
      if (next.has(cat)) next.delete(cat);
      else next.add(cat);
      return next;
    });

  return (
    <>
      <div className="perm-groups">
        {categories.map((cat) => {
          const perms = permsByCategory[cat];
          const slugs = perms.map((p) => p.slug);
          const grantedCount = slugs.filter((s) => editor.isGranted(s)).length;
          const Icon = categoryIcon(cat);
          const isOpen = !collapsed.has(cat);
          return (
            <div key={cat} className="perm-group">
              <div className="perm-group-head" role="group">
                <button
                  type="button"
                  className="perm-group-head"
                  style={{ padding: 0, background: 'transparent', flex: 1 }}
                  onClick={() => toggleCollapse(cat)}
                >
                  {isOpen ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
                  <Icon size={16} />
                  <span className="perm-group-title">
                    <strong>{t(`roles.permissionCategories.${cat}`, cat)}</strong>
                    <span>{t(`roles.categoryDescriptions.${cat}`, '')}</span>
                  </span>
                  <span className="perm-group-count">
                    {grantedCount}/{slugs.length}
                  </span>
                </button>
                <span className="perm-bulk">
                  <button type="button" onClick={() => editor.toggleCategory(slugs, true)}>
                    {t('roles.grantAll')}
                  </button>
                  <button type="button" onClick={() => editor.toggleCategory(slugs, false)}>
                    {t('roles.revokeAll')}
                  </button>
                </span>
              </div>

              {isOpen && (
                <div className="perm-group-body">
                  {perms.map((p) => {
                    const granted = editor.isGranted(p.slug);
                    const changed = role.permissions.includes(p.slug) !== granted;
                    return (
                      <label key={p.slug} className={`perm-row ${changed ? 'changed' : ''}`}>
                        <button
                          type="button"
                          className={`perm-check ${granted ? 'on' : ''}`}
                          onClick={() => editor.toggle(p.slug)}
                          aria-pressed={granted}
                        >
                          {granted && <Check size={12} />}
                        </button>
                        <span className="perm-slug">{p.slug}</span>
                        <span className="perm-desc">{describe(p)}</span>
                      </label>
                    );
                  })}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {editor.dirty && (
        <div className="save-bar">
          <span className="save-bar-msg">
            <span className="diff-badge">{editor.diffCount}</span>
            {t('roles.unsavedChanges', { count: editor.diffCount })}
          </span>
          <span className="save-bar-actions">
            <button
              className="admin-btn admin-btn-ghost"
              onClick={editor.discard}
              disabled={editor.saving}
            >
              <Undo2 size={14} /> {t('roles.discard')}
            </button>
            <button
              className="admin-btn admin-btn-primary"
              onClick={() => void editor.save()}
              disabled={editor.saving}
            >
              <Save size={14} /> {t('roles.saveChanges')}
            </button>
          </span>
        </div>
      )}
    </>
  );
};

export default PermissionMatrix;
