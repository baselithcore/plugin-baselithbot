/**
 * Local state for the Roles screen: template fetching and the staged permission
 * editor that powers the diff badges + floating save bar.
 */

import { useCallback, useEffect, useMemo, useState } from 'react';
import type { RbacRole, RoleTemplate } from '../../../types';
import * as rbac from '../../../api/rbac';

const TAB_PREFIX = 'tab:';

/** Fetch the predefined role templates once (non-fatal on error). */
export function useRoleTemplates(): RoleTemplate[] {
  const [templates, setTemplates] = useState<RoleTemplate[]>([]);
  useEffect(() => {
    let alive = true;
    rbac
      .listRoleTemplates()
      .then((t) => alive && setTemplates(t))
      .catch(() => alive && setTemplates([]));
    return () => {
      alive = false;
    };
  }, []);
  return templates;
}

export interface RoleEditor {
  staged: Set<string>;
  dirty: boolean;
  diffCount: number;
  saving: boolean;
  isGranted: (slug: string) => boolean;
  toggle: (slug: string) => void;
  toggleCategory: (slugs: string[], grant: boolean) => void;
  save: () => Promise<void>;
  discard: () => void;
}

/**
 * Stages permission changes for a single role locally so the admin can review a
 * diff and save in one batch. Only non-tab permissions are edited here; the
 * role's existing ``tab:*`` grants (managed in the Access Control tab) are
 * preserved untouched when saving.
 */
export function useRoleEditor(
  role: RbacRole | null,
  onSaved: () => Promise<void> | void
): RoleEditor {
  const original = useMemo(
    () => (role ? role.permissions.filter((p) => !p.startsWith(TAB_PREFIX)) : ([] as string[])),
    [role]
  );
  const [staged, setStaged] = useState<Set<string>>(() => new Set(original));
  const [saving, setSaving] = useState(false);

  // Reset the staging set whenever a different role is selected.
  useEffect(() => {
    setStaged(new Set(original));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [role?.id]);

  const isGranted = useCallback((slug: string) => staged.has(slug), [staged]);

  const toggle = useCallback((slug: string) => {
    setStaged((prev) => {
      const next = new Set(prev);
      if (next.has(slug)) next.delete(slug);
      else next.add(slug);
      return next;
    });
  }, []);

  const toggleCategory = useCallback((slugs: string[], grant: boolean) => {
    setStaged((prev) => {
      const next = new Set(prev);
      for (const s of slugs) {
        if (grant) next.add(s);
        else next.delete(s);
      }
      return next;
    });
  }, []);

  const diffCount = useMemo(() => {
    const orig = new Set(original);
    let n = 0;
    for (const s of staged) if (!orig.has(s)) n++;
    for (const s of orig) if (!staged.has(s)) n++;
    return n;
  }, [original, staged]);

  const discard = useCallback(() => setStaged(new Set(original)), [original]);

  const save = useCallback(async () => {
    if (!role) return;
    setSaving(true);
    try {
      // Preserve hidden tab:* grants; replace only the non-tab set.
      const tabPerms = role.permissions.filter((p) => p.startsWith(TAB_PREFIX));
      await rbac.setRolePermissions(role.id, [...tabPerms, ...staged]);
      await onSaved();
    } finally {
      setSaving(false);
    }
  }, [role, staged, onSaved]);

  return {
    staged,
    dirty: diffCount > 0,
    diffCount,
    saving,
    isGranted,
    toggle,
    toggleCategory,
    save,
    discard,
  };
}
