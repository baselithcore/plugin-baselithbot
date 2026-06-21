/**
 * AuthContext — adapter over the shared central ``@auth`` plugin.
 *
 * The wiki no longer owns identity, login, sessions or RBAC: the React app is
 * wrapped by ``@auth``'s ``AuthProvider`` + ``ProtectedRoute`` (see main.tsx),
 * which authenticate the user against the central auth plugin. This context is
 * a thin adapter that:
 *
 *  - re-exposes the SAME ``useAuth()`` surface the wiki's ~13 components already
 *    consume (``user``, ``can``/``canAny``/``canAll``, ``hasRole``, ``ready``,
 *    ``logout``…), so none of them had to change;
 *  - resolves the caller's wiki permission set from ``/api/me/perms`` (backed by
 *    :mod:`llm_wiki.auth._core_bridge`), mapping the central identity onto the
 *    engine's permission vocabulary.
 *
 * Login/registration are intentionally inert here — the central login wall owns
 * them. ``can()`` is a UI convenience; the backend re-checks every permission.
 */

import {
  type ReactNode,
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from 'react';

import { useAuth as useCoreAuth } from '@auth';

import type { AuthUser, RegisterArgs } from '../lib/api/auth';
import { json, onAuthEvent } from '../lib/api/client';

interface MePerms {
  user_id: string;
  email: string;
  display_name: string;
  role: 'admin' | 'user';
  is_admin: boolean;
  perms: string[];
  roles: string[];
}

interface AuthContextValue {
  user: AuthUser | null;
  loading: boolean;
  /** primo bootstrap finito (identità + permessi risolti) — gating App */
  ready: boolean;
  /** Sempre true: l'auth centrale è la sola fonte d'identità. */
  authEnabled: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (args: RegisterArgs) => Promise<void>;
  logout: () => Promise<void>;
  logoutAll: () => Promise<void>;
  refreshUser: () => Promise<void>;
  /** RBAC: true se ``user`` ha ``perm`` (admin = wildcard). */
  can: (perm: string) => boolean;
  canAny: (perms: string[]) => boolean;
  canAll: (perms: string[]) => boolean;
  hasRole: (role: string) => boolean;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const core = useCoreAuth();
  const [perms, setPerms] = useState<MePerms | null>(null);
  const [permsReady, setPermsReady] = useState(false);

  const loadPerms = useCallback(async () => {
    if (!core.isAuthenticated) {
      setPerms(null);
      setPermsReady(true);
      return;
    }
    try {
      setPerms(await json<MePerms>('/me/perms'));
    } catch {
      setPerms(null);
    } finally {
      setPermsReady(true);
    }
  }, [core.isAuthenticated]);

  // (Re)load the wiki permission map whenever the central identity changes.
  useEffect(() => {
    setPermsReady(false);
    void loadPerms();
  }, [loadPerms, core.user?.id]);

  // A 401 from the wiki API means the central session lapsed → hand back to the
  // central login wall.
  useEffect(() => onAuthEvent('auth:logout', () => void core.logout()), [core]);

  const user = useMemo<AuthUser | null>(() => {
    if (!core.user) return null;
    return {
      id: core.user.id,
      email: core.user.email,
      display_name: perms?.display_name ?? core.user.username ?? core.user.email,
      tenant_id: core.user.id,
      role: perms?.role ?? 'user',
      is_active: true,
      roles: perms?.roles ?? core.user.roles ?? [],
      permissions: perms?.perms ?? [],
    };
  }, [core.user, perms]);

  const isAdmin = perms?.is_admin ?? false;
  const permSet = useMemo(() => new Set(perms?.perms ?? []), [perms]);
  const roleSet = useMemo(
    () => new Set([...(perms?.roles ?? []), ...(core.user?.roles ?? [])]),
    [perms, core.user?.roles]
  );

  const can = useCallback((perm: string) => isAdmin || permSet.has(perm), [isAdmin, permSet]);
  const canAny = useCallback(
    (list: string[]) => isAdmin || list.some((p) => permSet.has(p)),
    [isAdmin, permSet]
  );
  const canAll = useCallback(
    (list: string[]) => isAdmin || list.every((p) => permSet.has(p)),
    [isAdmin, permSet]
  );
  const hasRole = useCallback(
    (role: string) => roleSet.has(role) || core.hasRole(role),
    [roleSet, core]
  );

  // Login/registration belong to the central auth plugin's login wall; these
  // remain only for source-compatibility with legacy call sites and are never
  // reached once ``ProtectedRoute`` is mounted.
  const login = useCallback(async (_email: string, _password: string) => {
    throw new Error('Login is handled by the central auth plugin');
  }, []);
  const register = useCallback(async (_args: RegisterArgs) => {
    throw new Error('Registration is handled by the central auth plugin');
  }, []);
  const logout = useCallback(async () => {
    await core.logout();
  }, [core]);
  const refreshUser = useCallback(async () => {
    await loadPerms();
  }, [loadPerms]);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      loading: core.isLoading,
      ready: !core.isLoading && permsReady,
      authEnabled: true,
      login,
      register,
      logout,
      logoutAll: logout,
      refreshUser,
      can,
      canAny,
      canAll,
      hasRole,
    }),
    [
      user,
      core.isLoading,
      permsReady,
      login,
      register,
      logout,
      refreshUser,
      can,
      canAny,
      canAll,
      hasRole,
    ]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth deve stare dentro <AuthProvider>');
  return ctx;
}
