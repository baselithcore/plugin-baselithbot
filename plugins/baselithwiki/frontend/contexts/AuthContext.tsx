/**
 * AuthContext (Fase 6).
 *
 * Strategia
 * =========
 * - Bootstrap mount: tenta `refresh()` con cookie httpOnly per ripristinare
 *   sessione persistita. Se OK → fetch /auth/me → user state. Se KO → `null`
 *   (App mostra AuthPage se Postgres+auth richiesti).
 * - Login/register/logout azioni esposte al tree.
 * - Listener su `auth:logout` event dal client wrapper: una request 401 con
 *   refresh fallito droppa lo user state automaticamente.
 *
 * Best practice 2026: access token vive solo in memoria (XSS-resistant).
 * Refresh cookie httpOnly + Secure + SameSite=Strict gestito dal browser.
 */

import {
  type ReactNode,
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';

import * as authApi from '../lib/api/auth';
import type { AuthUser, RegisterArgs } from '../lib/api/auth';
import { ApiError, onAuthEvent, setAccessToken } from '../lib/api/client';

interface AuthContextValue {
  user: AuthUser | null;
  loading: boolean;
  /** primo bootstrap finito (refresh tentato). usalo per gating App */
  ready: boolean;
  /**
   * False quando il backend auth NON è montato (setup mode / Postgres off:
   * ``/auth/*`` risponde 404). App.tsx lo usa per NON gateare su AuthPage
   * quando non esiste alcun backend di autenticazione — la wiki è pubblica.
   */
  authEnabled: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (args: RegisterArgs) => Promise<void>;
  logout: () => Promise<void>;
  logoutAll: () => Promise<void>;
  refreshUser: () => Promise<void>;
  /** RBAC: true se ``user`` ha ``perm``. Falso se anonimo o senza grants. */
  can: (perm: string) => boolean;
  /** True se possiede uno qualsiasi dei permessi. */
  canAny: (perms: string[]) => boolean;
  /** True se possiede tutti i permessi. */
  canAll: (perms: string[]) => boolean;
  /** True se possiede il ruolo (slug). */
  hasRole: (role: string) => boolean;
}

const AuthContext = createContext<AuthContextValue | null>(null);

interface AuthProviderProps {
  children: ReactNode;
}

export function AuthProvider({ children }: AuthProviderProps) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(false);
  const [ready, setReady] = useState(false);
  const [authEnabled, setAuthEnabled] = useState(true);
  const bootstrapped = useRef(false);

  // Bootstrap iniziale: refresh + me. Idempotent via `bootstrapped` ref
  // (StrictMode-safe). NIENTE flag `cancelled`: in StrictMode dev, cleanup
  // del primo mount setta cancelled=true e blocca `setReady(true)` nel
  // finally → blank page infinita. Il ref ferma il doppio fetch; le
  // setState dopo unmount sono no-op innocui (React warning solo in dev).
  useEffect(() => {
    if (bootstrapped.current) return;
    bootstrapped.current = true;

    (async () => {
      setLoading(true);
      try {
        const r = await authApi.refresh();
        if (r) {
          try {
            const me = await authApi.me();
            setUser(me);
          } catch {
            setUser(null);
          }
        } else {
          setUser(null);
        }
      } catch (err) {
        // 404 = router /auth non montato (setup mode / Postgres off): la
        // wiki è pubblica, nessun gate. Altri errori → utente anonimo ma
        // auth potenzialmente attiva (rete/5xx).
        if (err instanceof ApiError && err.status === 404) {
          setAuthEnabled(false);
        }
        setUser(null);
      } finally {
        setLoading(false);
        setReady(true);
      }
    })();
  }, []);

  // Listener: 401 + refresh fallito dal client wrapper → logout state.
  useEffect(() => {
    return onAuthEvent('auth:logout', () => {
      setUser(null);
    });
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    setLoading(true);
    try {
      await authApi.login(email, password);
      const me = await authApi.me();
      setUser(me);
    } finally {
      setLoading(false);
    }
  }, []);

  const register = useCallback(async (args: RegisterArgs) => {
    setLoading(true);
    try {
      await authApi.register(args);
      const me = await authApi.me();
      setUser(me);
    } finally {
      setLoading(false);
    }
  }, []);

  const logout = useCallback(async () => {
    setLoading(true);
    try {
      await authApi.logout();
    } finally {
      setAccessToken(null);
      setUser(null);
      setLoading(false);
    }
  }, []);

  const logoutAll = useCallback(async () => {
    setLoading(true);
    try {
      await authApi.logoutAll();
    } finally {
      setAccessToken(null);
      setUser(null);
      setLoading(false);
    }
  }, []);

  const refreshUser = useCallback(async () => {
    try {
      const me = await authApi.me();
      setUser(me);
    } catch {
      setUser(null);
    }
  }, []);

  // RBAC helpers — derivati da `user.permissions` / `user.roles`.
  // `admin` (legacy column) bypassa qualsiasi check di permesso per
  // back-compat: prima del rollout RBAC i super-user usavano solo `role`.
  const permSet = useMemo(() => new Set(user?.permissions ?? []), [user?.permissions]);
  const roleSet = useMemo(
    () => new Set([...(user?.roles ?? []), ...(user?.role ? [user.role] : [])]),
    [user?.roles, user?.role]
  );
  const isLegacyAdmin = user?.role === 'admin';

  const can = useCallback(
    (perm: string) => isLegacyAdmin || permSet.has(perm),
    [isLegacyAdmin, permSet]
  );
  const canAny = useCallback(
    (perms: string[]) => isLegacyAdmin || perms.some((p) => permSet.has(p)),
    [isLegacyAdmin, permSet]
  );
  const canAll = useCallback(
    (perms: string[]) => isLegacyAdmin || perms.every((p) => permSet.has(p)),
    [isLegacyAdmin, permSet]
  );
  const hasRole = useCallback((role: string) => roleSet.has(role), [roleSet]);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      loading,
      ready,
      authEnabled,
      login,
      register,
      logout,
      logoutAll,
      refreshUser,
      can,
      canAny,
      canAll,
      hasRole,
    }),
    [
      user,
      loading,
      ready,
      authEnabled,
      login,
      register,
      logout,
      logoutAll,
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
