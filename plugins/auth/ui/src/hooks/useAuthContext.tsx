/**
 * Auth Context and Hook
 *
 * React context for authentication state management.
 */

import { createContext, useContext, useCallback, useEffect, useState, type ReactNode } from 'react';
import type {
  UserInfo,
  AccessibleTab,
  Impersonator,
  MFAEnrollmentRequiredResponse,
} from '../api/auth';
import {
  login as apiLogin,
  verifyMFA as apiVerifyMFA,
  enrollVerifyMFA as apiEnrollVerifyMFA,
  logout as apiLogout,
  refreshToken as apiRefreshToken,
  startImpersonation as apiStartImpersonation,
  stopImpersonation as apiStopImpersonation,
  getCurrentUser,
  getAccessibleTabs,
  isMFARequired,
  isMFAEnrollmentRequired,
} from '../api/auth';

/** Result of a login attempt — may require an MFA challenge or forced enrollment. */
export interface LoginResult {
  mfaRequired: boolean;
  tempToken?: string;
  mfaEnrollmentRequired?: boolean;
  enrollment?: MFAEnrollmentRequiredResponse;
}

export interface AuthState {
  isAuthenticated: boolean;
  isLoading: boolean;
  user: UserInfo | null;
  accessToken: string | null;
  error: string | null;
  mfaRequired: boolean;
  mfaTempToken: string | null;
}

export interface AuthContextValue extends AuthState {
  login: (email: string, password: string) => Promise<LoginResult>;
  verifyMFA: (tempToken: string, code: string) => Promise<void>;
  /** Complete a policy-forced MFA enrollment, then finish login. */
  enrollVerify: (enrollToken: string, code: string) => Promise<void>;
  logout: () => Promise<void>;
  refreshAuth: () => Promise<void>;
  canAccessTab: (tabId: string, plugin?: string) => boolean;
  hasRole: (role: string) => boolean;
  /** Begin impersonating a user (admin only). Swaps the active session token. */
  impersonate: (userId: string, reason?: string) => Promise<void>;
  /** End the current impersonation session and restore the administrator. */
  stopImpersonation: () => Promise<void>;
  /** Whether the current session is an admin acting as another user. */
  isImpersonating: boolean;
  /** The real administrator behind an active impersonation session. */
  impersonator: Impersonator | null;
}

const defaultContext: AuthContextValue = {
  isAuthenticated: false,
  isLoading: true,
  user: null,
  accessToken: null,
  error: null,
  mfaRequired: false,
  mfaTempToken: null,
  login: async () => ({ mfaRequired: false }),
  verifyMFA: async () => {},
  enrollVerify: async () => {},
  logout: async () => {},
  refreshAuth: async () => {},
  canAccessTab: () => true,
  hasRole: () => false,
  impersonate: async () => {},
  stopImpersonation: async () => {},
  isImpersonating: false,
  impersonator: null,
};

export const AuthContext = createContext<AuthContextValue>(defaultContext);

/**
 * Hook to access auth context.
 */
export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}

interface AuthProviderProps {
  children: ReactNode;
}

const TOKEN_KEY = 'auth_access_token';
const TOKEN_EXPIRY_KEY = 'auth_token_expiry';

/**
 * AuthProvider Component
 *
 * Manages authentication state and provides auth context.
 */
export function AuthProvider({ children }: AuthProviderProps) {
  const [state, setState] = useState<AuthState>({
    isAuthenticated: false,
    isLoading: true,
    user: null,
    accessToken: null,
    error: null,
    mfaRequired: false,
    mfaTempToken: null,
  });

  // Central per-tab access policy (from /api/auth/access/tabs). Empty until
  // loaded; canAccessTab defaults to allow while unknown to avoid flicker.
  const [accessibleTabs, setAccessibleTabs] = useState<AccessibleTab[] | null>(null);

  // Fetch the central tab policy whenever an access token becomes available.
  useEffect(() => {
    if (!state.isAuthenticated || !state.accessToken) {
      setAccessibleTabs(null);
      return;
    }
    let cancelled = false;
    getAccessibleTabs(state.accessToken)
      .then((tabs) => {
        if (!cancelled) setAccessibleTabs(tabs);
      })
      .catch(() => {
        if (!cancelled) setAccessibleTabs(null); // fail-open
      });
    return () => {
      cancelled = true;
    };
  }, [state.isAuthenticated, state.accessToken]);

  // Load token from storage on mount. The access token lives in localStorage
  // (shared across all same-origin tabs/windows) so opening another plugin —
  // e.g. launched from baselithcontrol with target="_blank" — inherits the
  // session immediately, with no re-login and no /refresh round-trip. The
  // sensitive long-lived refresh token stays in an httpOnly cookie.
  useEffect(() => {
    const handleUnauthorized = () => {
      setState((s) => ({
        ...s,
        isAuthenticated: false,
        user: null,
        accessToken: null,
      }));
      clearToken();
    };

    // Cross-tab session sync: a login or logout in any other tab fires a
    // `storage` event here. Adopt a new session, or drop ours when cleared.
    const handleStorage = (e: StorageEvent) => {
      if (e.key !== TOKEN_KEY) return;
      if (e.newValue) {
        loadUser(e.newValue);
      } else {
        setState((s) => ({
          ...s,
          isAuthenticated: false,
          user: null,
          accessToken: null,
        }));
      }
    };

    window.addEventListener('auth:unauthorized', handleUnauthorized);
    window.addEventListener('storage', handleStorage);

    const storedToken = localStorage.getItem(TOKEN_KEY);
    const storedExpiry = localStorage.getItem(TOKEN_EXPIRY_KEY);
    if (storedToken && storedExpiry && parseInt(storedExpiry, 10) > Date.now()) {
      loadUser(storedToken);
    } else {
      tryRefresh();
    }

    return () => {
      window.removeEventListener('auth:unauthorized', handleUnauthorized);
      window.removeEventListener('storage', handleStorage);
    };
  }, []);

  const loadUser = async (token: string) => {
    try {
      const user = await getCurrentUser(token);
      setState({
        isAuthenticated: true,
        isLoading: false,
        user,
        accessToken: token,
        error: null,
        mfaRequired: false,
        mfaTempToken: null,
      });
    } catch {
      tryRefresh();
    }
  };

  const tryRefresh = async () => {
    try {
      const response = await apiRefreshToken();
      storeToken(response.access_token, response.expires_in);
      const user = await getCurrentUser(response.access_token);
      setState({
        isAuthenticated: true,
        isLoading: false,
        user,
        accessToken: response.access_token,
        error: null,
        mfaRequired: false,
        mfaTempToken: null,
      });
    } catch {
      clearToken();
      setState((s) => ({
        isAuthenticated: false,
        isLoading: false,
        user: null,
        accessToken: null,
        error: null,
        mfaRequired: s.mfaRequired,
        mfaTempToken: s.mfaTempToken,
      }));
    }
  };

  const storeToken = (token: string, expiresIn: number) => {
    const expiry = Date.now() + expiresIn * 1000;
    localStorage.setItem(TOKEN_KEY, token);
    localStorage.setItem(TOKEN_EXPIRY_KEY, expiry.toString());
  };

  const clearToken = () => {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(TOKEN_EXPIRY_KEY);
  };

  const login = useCallback(async (email: string, password: string): Promise<LoginResult> => {
    setState((s) => ({ ...s, error: null, isLoading: true }));

    try {
      const response = await apiLogin(email, password);

      if (isMFARequired(response)) {
        setState((s) => ({
          ...s,
          isLoading: false,
          mfaRequired: true,
          mfaTempToken: response.temp_token,
        }));
        return { mfaRequired: true, tempToken: response.temp_token };
      }

      if (isMFAEnrollmentRequired(response)) {
        // Policy mandates MFA but the user has not enrolled — no session yet.
        setState((s) => ({ ...s, isLoading: false }));
        return { mfaRequired: false, mfaEnrollmentRequired: true, enrollment: response };
      }

      storeToken(response.access_token, response.expires_in);
      const user = await getCurrentUser(response.access_token);

      setState({
        isAuthenticated: true,
        isLoading: false,
        user,
        accessToken: response.access_token,
        error: null,
        mfaRequired: false,
        mfaTempToken: null,
      });

      return { mfaRequired: false };
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Login failed';
      setState((s) => ({ ...s, isLoading: false, error: message }));
      throw err;
    }
  }, []);

  const verifyMFA = useCallback(async (tempToken: string, code: string) => {
    setState((s) => ({ ...s, error: null, isLoading: true }));

    try {
      const response = await apiVerifyMFA(tempToken, code);
      storeToken(response.access_token, response.expires_in);
      const user = await getCurrentUser(response.access_token);

      setState({
        isAuthenticated: true,
        isLoading: false,
        user,
        accessToken: response.access_token,
        error: null,
        mfaRequired: false,
        mfaTempToken: null,
      });
    } catch (err) {
      const message = err instanceof Error ? err.message : 'MFA verification failed';
      setState((s) => ({ ...s, isLoading: false, error: message }));
      throw err;
    }
  }, []);

  const enrollVerify = useCallback(async (enrollToken: string, code: string) => {
    setState((s) => ({ ...s, error: null, isLoading: true }));

    try {
      const response = await apiEnrollVerifyMFA(enrollToken, code);
      storeToken(response.access_token, response.expires_in);
      const user = await getCurrentUser(response.access_token);

      setState({
        isAuthenticated: true,
        isLoading: false,
        user,
        accessToken: response.access_token,
        error: null,
        mfaRequired: false,
        mfaTempToken: null,
      });
    } catch (err) {
      const message = err instanceof Error ? err.message : 'MFA verification failed';
      setState((s) => ({ ...s, isLoading: false, error: message }));
      throw err;
    }
  }, []);

  const logout = useCallback(async () => {
    try {
      await apiLogout();
    } finally {
      clearToken();
      setState({
        isAuthenticated: false,
        isLoading: false,
        user: null,
        accessToken: null,
        error: null,
        mfaRequired: false,
        mfaTempToken: null,
      });
    }
  }, []);

  const refreshAuth = useCallback(async () => {
    await tryRefresh();
  }, []);

  const impersonate = useCallback(async (userId: string, reason?: string) => {
    const token = localStorage.getItem(TOKEN_KEY);
    if (!token) throw new Error('Not authenticated');
    const resp = await apiStartImpersonation(token, userId, reason);
    storeToken(resp.access_token, resp.expires_in);
    await loadUser(resp.access_token);
  }, []);

  const stopImpersonation = useCallback(async () => {
    const token = localStorage.getItem(TOKEN_KEY);
    if (!token) {
      await tryRefresh();
      return;
    }
    try {
      const resp = await apiStopImpersonation(token);
      storeToken(resp.access_token, resp.expires_in);
      await loadUser(resp.access_token);
    } catch {
      // The admin's own refresh session was never touched, so a plain refresh
      // restores the administrator even if the stop call fails.
      await tryRefresh();
    }
  }, []);

  const canAccessTab = useCallback(
    (tabId: string, plugin?: string): boolean => {
      // Policy not loaded yet -> allow (avoid flicker / accidental lockout).
      if (accessibleTabs === null) return true;
      const matches = accessibleTabs.filter(
        (t) => t.tab_id === tabId && (!plugin || t.plugin === plugin)
      );
      // Unmanaged tab (not in policy) -> default-allow. Otherwise allow when
      // at least one matching entry is allowed.
      if (matches.length === 0) return true;
      return matches.some((t) => t.allowed);
    },
    [accessibleTabs]
  );

  const hasRole = useCallback(
    (role: string): boolean => {
      if (!state.user) return false;
      return state.user.roles.includes(role);
    },
    [state.user]
  );

  return (
    <AuthContext.Provider
      value={{
        ...state,
        login,
        verifyMFA,
        enrollVerify,
        logout,
        refreshAuth,
        canAccessTab,
        hasRole,
        impersonate,
        stopImpersonation,
        isImpersonating: !!state.user?.is_impersonating,
        impersonator: state.user?.impersonator ?? null,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}
