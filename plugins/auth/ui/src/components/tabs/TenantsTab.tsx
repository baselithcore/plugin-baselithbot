/**
 * Tenants tab — provision tenants and assign users (enterprise multi-tenancy).
 *
 * Left: tenant list. Right: selected tenant's status (active/suspended),
 * members (add/remove), and delete. A user's first tenant becomes their
 * default; their access token is scoped to it (see plugins/auth/tenancy.py).
 */

import { useCallback, useEffect, useMemo, useState } from 'react';
import { Building2, Plus, Trash2, UserPlus, X, Power, Search } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import * as tenants from '../../api/tenants';
import { listUsers } from '../../api/users';
import PageHeader from '../shared/PageHeader';
import type { Tenant, TenantMember, User } from '../../types';

const TenantsTab = () => {
  const { t } = useTranslation();
  const [list, setList] = useState<Tenant[]>([]);
  const [users, setUsers] = useState<User[]>([]);
  const [members, setMembers] = useState<TenantMember[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [form, setForm] = useState({ slug: '', name: '' });
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState('');

  const selected = list.find((x) => x.id === selectedId) || null;
  const visible = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return list;
    return list.filter(
      (tn) => tn.name.toLowerCase().includes(q) || tn.slug.toLowerCase().includes(q)
    );
  }, [list, query]);

  const reload = useCallback(async () => {
    try {
      const [ts, u] = await Promise.all([tenants.listTenants(), listUsers(1, 100)]);
      setList(ts);
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
    tenants
      .listMembers(selectedId)
      .then(setMembers)
      .catch(() => setMembers([]));
  }, [selectedId]);

  const memberIds = useMemo(() => new Set(members.map((m) => m.user_id)), [members]);
  const nonMembers = useMemo(() => users.filter((u) => !memberIds.has(u.id)), [users, memberIds]);

  const run = async (fn: () => Promise<unknown>) => {
    try {
      await fn();
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'error');
    }
  };

  const handleCreate = () =>
    run(async () => {
      if (!form.slug || !form.name) return;
      await tenants.createTenant(form.slug.trim(), form.name.trim());
      setForm({ slug: '', name: '' });
      setCreating(false);
      await reload();
    });

  const handleDelete = (tn: Tenant) =>
    run(async () => {
      if (!window.confirm(t('tenants.deleteConfirm', { name: tn.name }))) return;
      await tenants.deleteTenant(tn.id);
      if (selectedId === tn.id) setSelectedId(null);
      await reload();
    });

  const toggleStatus = (tn: Tenant) =>
    run(async () => {
      await tenants.setTenantStatus(tn.id, tn.status === 'active' ? 'suspended' : 'active');
      await reload();
    });

  const addMember = (userId: string) =>
    run(async () => {
      if (!selected) return;
      await tenants.addMember(selected.id, userId);
      setMembers(await tenants.listMembers(selected.id));
      await reload();
    });

  const removeMember = (userId: string) =>
    run(async () => {
      if (!selected) return;
      await tenants.removeMember(selected.id, userId);
      setMembers(await tenants.listMembers(selected.id));
      await reload();
    });

  return (
    <div className="tenants-tab">
      <PageHeader
        icon={<Building2 size={22} />}
        title={t('tenants.title')}
        subtitle={t('tenants.description')}
        countLabel={t('tenants.countLabel', { count: list.length })}
        actions={
          <>
            <div className="admin-search">
              <Search size={15} />
              <input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder={t('tenants.searchPlaceholder')}
                aria-label={t('tenants.searchPlaceholder')}
              />
            </div>
            <button className="admin-btn admin-btn-primary" onClick={() => setCreating(true)}>
              <Plus size={16} /> {t('tenants.addTenant')}
            </button>
          </>
        }
      />

      {error && <div className="admin-alert admin-alert-error">{error}</div>}

      {creating && (
        <div className="admin-card tenant-create">
          <input
            className="admin-input"
            placeholder={t('tenants.slug')}
            value={form.slug}
            onChange={(e) => setForm({ ...form, slug: e.target.value })}
          />
          <input
            className="admin-input"
            placeholder={t('tenants.name')}
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
          />
          <button className="admin-btn admin-btn-primary" onClick={handleCreate}>
            {t('common.create')}
          </button>
          <button className="admin-btn admin-btn-ghost" onClick={() => setCreating(false)}>
            {t('common.cancel')}
          </button>
        </div>
      )}

      <div className="tenants-grid">
        <div className="tenants-list">
          {visible.map((tn) => (
            <button
              key={tn.id}
              className={`tenant-item ${selected?.id === tn.id ? 'active' : ''}`}
              onClick={() => setSelectedId(tn.id)}
            >
              <span className="tenant-item-name">
                {tn.name}
                {tn.status !== 'active' && (
                  <span className="tenant-badge suspended">{t('tenants.suspended')}</span>
                )}
              </span>
              <span className="tenant-item-meta">
                {tn.slug} · {t('tenants.memberCount', { count: tn.member_count })}
              </span>
            </button>
          ))}
          {visible.length === 0 && (
            <p className="admin-empty-text">
              {query ? t('tenants.noMatches') : t('tenants.empty')}
            </p>
          )}
        </div>

        {selected && (
          <div className="admin-card tenant-detail">
            <div className="tenant-detail-head">
              <div>
                <h3>{selected.name}</h3>
                <code className="tenant-slug">{selected.slug}</code>
              </div>
              <div className="tenant-detail-actions">
                <button
                  className="admin-btn admin-btn-ghost admin-btn-icon"
                  onClick={() => toggleStatus(selected)}
                  title={
                    selected.status === 'active' ? t('tenants.suspend') : t('tenants.activate')
                  }
                  style={{
                    color: selected.status === 'active' ? undefined : 'var(--admin-success)',
                  }}
                >
                  <Power size={16} />
                </button>
                <button
                  className="admin-btn admin-btn-ghost admin-btn-icon"
                  onClick={() => handleDelete(selected)}
                  title={t('common.delete')}
                >
                  <Trash2 size={16} />
                </button>
              </div>
            </div>

            <h4>{t('tenants.members')}</h4>
            <div className="tenant-members">
              {members.map((m) => (
                <div key={m.user_id} className="tenant-member-row">
                  <span>
                    {m.username || m.email}
                    {m.is_default && <span className="tenant-badge">{t('tenants.default')}</span>}
                  </span>
                  <button
                    type="button"
                    className="admin-btn admin-btn-ghost admin-btn-icon"
                    onClick={() => removeMember(m.user_id)}
                    title={t('tenants.removeMember')}
                  >
                    <X size={14} />
                  </button>
                </div>
              ))}
              {members.length === 0 && <p className="admin-empty-text">{t('tenants.noMembers')}</p>}
            </div>

            {nonMembers.length > 0 && (
              <div className="tenant-add-member">
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
                    {t('tenants.addMember')}
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
        .tenants-tab { display: flex; flex-direction: column; gap: 1rem; }
        .tenant-create { display: flex; gap: 0.5rem; flex-wrap: wrap; padding: 1rem; }
        .tenants-grid { display: grid; grid-template-columns: 280px 1fr; gap: 1rem; align-items: start; }
        .tenants-list { display: flex; flex-direction: column; gap: 0.5rem; }
        .tenant-item { text-align: left; padding: 0.75rem; border-radius: 0.5rem;
          background: var(--admin-surface, hsla(220,25%,15%,0.5)); border: 1px solid transparent;
          cursor: pointer; display: flex; flex-direction: column; gap: 0.25rem; color: var(--admin-text); }
        .tenant-item.active { border-color: var(--admin-accent); }
        .tenant-item-name { font-weight: 600; display: flex; align-items: center; gap: 0.5rem; }
        .tenant-item-meta { font-size: 0.72rem; color: var(--admin-text-muted); }
        .tenant-badge { font-size: 0.62rem; text-transform: uppercase; letter-spacing: 0.03em;
          padding: 0.1rem 0.4rem; border-radius: 9999px; background: var(--admin-accent); color: #fff; }
        .tenant-badge.suspended { background: hsla(30,90%,55%,0.25); color: #f59e0b; }
        .tenant-detail { padding: 1.25rem; }
        .tenant-detail-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 0.75rem; }
        .tenant-detail-head h3 { margin: 0 0 0.25rem; }
        .tenant-detail-actions { display: flex; gap: 0.25rem; }
        .tenant-detail h4 { margin: 1rem 0 0.5rem; font-size: 0.8rem; text-transform: uppercase; color: var(--admin-text-muted); }
        .tenant-slug { font-size: 0.75rem; color: var(--admin-text-muted); }
        .tenant-members { display: flex; flex-direction: column; gap: 0.35rem; }
        .tenant-member-row { display: flex; align-items: center; justify-content: space-between;
          padding: 0.35rem 0.5rem; border-radius: 0.4rem; background: hsla(220,25%,18%,0.4); }
        .tenant-member-row span { display: flex; align-items: center; gap: 0.5rem; }
        .tenant-add-member { display: flex; align-items: center; gap: 0.5rem; margin-top: 0.75rem; }
        @media (max-width: 820px) { .tenants-grid { grid-template-columns: 1fr; } }
      `}</style>
    </div>
  );
};

export default TenantsTab;
