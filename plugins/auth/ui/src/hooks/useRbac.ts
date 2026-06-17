/**
 * Data hook for the RBAC admin screens (roles, permissions, tab policy).
 */

import { useCallback, useEffect, useState } from 'react';
import type { RbacPermission, RbacRole, TabPolicy } from '../types';
import * as rbac from '../api/rbac';

export function useRbac() {
  const [roles, setRoles] = useState<RbacRole[]>([]);
  const [permissions, setPermissions] = useState<RbacPermission[]>([]);
  const [tabs, setTabs] = useState<TabPolicy[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const reload = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [r, p, t] = await Promise.all([
        rbac.listRoles(),
        rbac.listPermissions(),
        rbac.listTabs(),
      ]);
      setRoles(r);
      setPermissions(p);
      setTabs(t);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'error');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void reload();
  }, [reload]);

  const refreshTabs = useCallback(async () => {
    setTabs(await rbac.refreshTabs());
  }, []);

  const toggleRestricted = useCallback(
    async (plugin: string, tabId: string, restricted: boolean) => {
      const updated = await rbac.setTabRestricted(plugin, tabId, restricted);
      setTabs((prev) => prev.map((t) => (t.plugin === plugin && t.tab_id === tabId ? updated : t)));
    },
    []
  );

  const togglePermission = useCallback(async (role: RbacRole, slug: string, granted: boolean) => {
    if (granted) {
      await rbac.grantPermission(role.id, slug);
    } else {
      await rbac.revokePermission(role.id, slug);
    }
    setRoles((prev) =>
      prev.map((r) =>
        r.id === role.id
          ? {
              ...r,
              permissions: granted
                ? [...r.permissions, slug]
                : r.permissions.filter((s) => s !== slug),
            }
          : r
      )
    );
  }, []);

  return {
    roles,
    permissions,
    tabs,
    loading,
    error,
    reload,
    refreshTabs,
    toggleRestricted,
    togglePermission,
    setRoles,
  };
}
