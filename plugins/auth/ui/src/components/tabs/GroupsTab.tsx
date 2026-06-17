/**
 * Groups tab — bundle users and assign roles in bulk (wikigen-style).
 *
 * Left: group list. Right: selected group's roles (toggle) and members
 * (add/remove). A user's effective permissions include every role of every
 * group they belong to.
 */

import { useCallback, useEffect, useMemo, useState } from 'react';
import { Users2, Plus, Trash2, Check, UserPlus, X } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import * as rbac from '../../api/rbac';
import { listUsers } from '../../api/users';
import type { RbacGroup, RbacRole, GroupMember, User } from '../../types';

const GroupsTab = () => {
  const { t } = useTranslation();
  const [groups, setGroups] = useState<RbacGroup[]>([]);
  const [roles, setRoles] = useState<RbacRole[]>([]);
  const [users, setUsers] = useState<User[]>([]);
  const [members, setMembers] = useState<GroupMember[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [form, setForm] = useState({ slug: '', name: '', description: '' });
  const [error, setError] = useState<string | null>(null);

  const selected = groups.find((g) => g.id === selectedId) || null;

  const reload = useCallback(async () => {
    try {
      const [g, r, u] = await Promise.all([rbac.listGroups(), rbac.listRoles(), listUsers(1, 100)]);
      setGroups(g);
      setRoles(r);
      setUsers(u.users);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'error');
    }
  }, []);

  useEffect(() => {
    void reload();
  }, [reload]);

  useEffect(() => {
    if (!selectedId) {
      setMembers([]);
      return;
    }
    rbac
      .listGroupMembers(selectedId)
      .then(setMembers)
      .catch(() => setMembers([]));
  }, [selectedId]);

  const memberIds = useMemo(() => new Set(members.map((m) => m.id)), [members]);
  const nonMembers = useMemo(() => users.filter((u) => !memberIds.has(u.id)), [users, memberIds]);

  const handleCreate = async () => {
    if (!form.slug || !form.name) return;
    try {
      await rbac.createGroup(form);
      setForm({ slug: '', name: '', description: '' });
      setCreating(false);
      await reload();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'error');
    }
  };

  const handleDelete = async (g: RbacGroup) => {
    if (!window.confirm(t('groups.deleteConfirm', { name: g.name }))) return;
    await rbac.deleteGroup(g.id);
    if (selectedId === g.id) setSelectedId(null);
    await reload();
  };

  const toggleRole = async (g: RbacGroup, role: RbacRole) => {
    const has = g.roles.includes(role.slug);
    if (has) await rbac.revokeGroupRole(g.id, role.id);
    else await rbac.assignGroupRole(g.id, role.id);
    await reload();
  };

  const addMember = async (userId: string) => {
    if (!selected) return;
    await rbac.addGroupMember(selected.id, userId);
    setMembers(await rbac.listGroupMembers(selected.id));
    await reload();
  };

  const removeMember = async (userId: string) => {
    if (!selected) return;
    await rbac.removeGroupMember(selected.id, userId);
    setMembers(await rbac.listGroupMembers(selected.id));
    await reload();
  };

  return (
    <div className="groups-tab">
      <div className="groups-header">
        <div className="groups-title">
          <Users2 size={20} />
          <h2>{t('groups.title')}</h2>
        </div>
        <button className="admin-btn admin-btn-primary" onClick={() => setCreating(true)}>
          <Plus size={16} /> {t('groups.addGroup')}
        </button>
      </div>
      <p className="groups-desc">{t('groups.description')}</p>

      {error && <div className="admin-alert admin-alert-error">{error}</div>}

      {creating && (
        <div className="admin-card group-create">
          <input
            className="admin-input"
            placeholder={t('groups.slug')}
            value={form.slug}
            onChange={(e) => setForm({ ...form, slug: e.target.value })}
          />
          <input
            className="admin-input"
            placeholder={t('groups.name')}
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
          />
          <input
            className="admin-input"
            placeholder={t('groups.descriptionField')}
            value={form.description}
            onChange={(e) => setForm({ ...form, description: e.target.value })}
          />
          <button className="admin-btn admin-btn-primary" onClick={handleCreate}>
            {t('common.create')}
          </button>
          <button className="admin-btn admin-btn-ghost" onClick={() => setCreating(false)}>
            {t('common.cancel')}
          </button>
        </div>
      )}

      <div className="groups-grid">
        <div className="groups-list">
          {groups.map((g) => (
            <button
              key={g.id}
              className={`group-item ${selected?.id === g.id ? 'active' : ''}`}
              onClick={() => setSelectedId(g.id)}
            >
              <span className="group-item-name">{g.name}</span>
              <span className="group-item-meta">
                {t('groups.memberCount', { count: g.member_count })} ·{' '}
                {t('groups.roleCount', { count: g.roles.length })}
              </span>
            </button>
          ))}
          {groups.length === 0 && <p className="admin-empty-text">{t('groups.empty')}</p>}
        </div>

        {selected && (
          <div className="admin-card group-detail">
            <div className="group-detail-head">
              <div>
                <h3>{selected.name}</h3>
                <code className="group-slug">{selected.slug}</code>
              </div>
              {!selected.is_system && (
                <button
                  className="admin-btn admin-btn-ghost admin-btn-icon"
                  onClick={() => handleDelete(selected)}
                  title={t('common.delete')}
                >
                  <Trash2 size={16} />
                </button>
              )}
            </div>

            <h4>{t('groups.roles')}</h4>
            <div className="group-roles">
              {roles.map((role) => {
                const on = selected.roles.includes(role.slug);
                return (
                  <button
                    key={role.id}
                    type="button"
                    className={`group-role-chip ${on ? 'on' : ''}`}
                    onClick={() => toggleRole(selected, role)}
                  >
                    {on && <Check size={12} />} {role.name}
                  </button>
                );
              })}
            </div>

            <h4>{t('groups.members')}</h4>
            <div className="group-members">
              {members.map((m) => (
                <div key={m.id} className="group-member-row">
                  <span>{m.username || m.email}</span>
                  <button
                    type="button"
                    className="admin-btn admin-btn-ghost admin-btn-icon"
                    onClick={() => removeMember(m.id)}
                    title={t('groups.removeMember')}
                  >
                    <X size={14} />
                  </button>
                </div>
              ))}
              {members.length === 0 && <p className="admin-empty-text">{t('groups.noMembers')}</p>}
            </div>

            {nonMembers.length > 0 && (
              <div className="group-add-member">
                <UserPlus size={14} />
                <select
                  className="admin-input"
                  defaultValue=""
                  onChange={(e) => {
                    if (e.target.value) {
                      addMember(e.target.value);
                      e.target.value = '';
                    }
                  }}
                >
                  <option value="" disabled>
                    {t('groups.addMember')}
                  </option>
                  {nonMembers.map((u) => (
                    <option key={u.id} value={u.id}>
                      {u.username || u.email}
                    </option>
                  ))}
                </select>
              </div>
            )}
          </div>
        )}
      </div>

      <style>{`
        .groups-tab { display: flex; flex-direction: column; gap: 0.75rem; }
        .groups-header { display: flex; align-items: center; justify-content: space-between; }
        .groups-title { display: flex; align-items: center; gap: 0.75rem; color: var(--admin-text); }
        .groups-title h2 { margin: 0; }
        .groups-desc { margin: 0; color: var(--admin-text-muted); font-size: 0.875rem; }
        .group-create { display: flex; gap: 0.5rem; flex-wrap: wrap; padding: 1rem; }
        .groups-grid { display: grid; grid-template-columns: 280px 1fr; gap: 1rem; align-items: start; }
        .groups-list { display: flex; flex-direction: column; gap: 0.5rem; }
        .group-item { text-align: left; padding: 0.75rem; border-radius: 0.5rem;
          background: var(--admin-surface, hsla(220,25%,15%,0.5)); border: 1px solid transparent;
          cursor: pointer; display: flex; flex-direction: column; gap: 0.25rem; color: var(--admin-text); }
        .group-item.active { border-color: var(--admin-accent); }
        .group-item-name { font-weight: 600; }
        .group-item-meta { font-size: 0.72rem; color: var(--admin-text-muted); }
        .group-detail { padding: 1.25rem; }
        .group-detail-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 0.75rem; }
        .group-detail-head h3 { margin: 0 0 0.25rem; }
        .group-detail h4 { margin: 1rem 0 0.5rem; font-size: 0.8rem; text-transform: uppercase; color: var(--admin-text-muted); }
        .group-slug { font-size: 0.75rem; color: var(--admin-text-muted); }
        .group-roles { display: flex; flex-wrap: wrap; gap: 0.4rem; }
        .group-role-chip { display: inline-flex; align-items: center; gap: 0.3rem; padding: 0.3rem 0.65rem;
          border-radius: 9999px; font-size: 0.78rem; cursor: pointer; color: var(--admin-text);
          background: hsla(220,25%,25%,0.4); border: 1px solid transparent; }
        .group-role-chip.on { background: var(--admin-accent); border-color: var(--admin-accent); color: #fff; }
        .group-members { display: flex; flex-direction: column; gap: 0.35rem; }
        .group-member-row { display: flex; align-items: center; justify-content: space-between;
          padding: 0.35rem 0.5rem; border-radius: 0.4rem; background: hsla(220,25%,18%,0.4); }
        .group-add-member { display: flex; align-items: center; gap: 0.5rem; margin-top: 0.75rem; }
        @media (max-width: 820px) { .groups-grid { grid-template-columns: 1fr; } }
      `}</style>
    </div>
  );
};

export default GroupsTab;
