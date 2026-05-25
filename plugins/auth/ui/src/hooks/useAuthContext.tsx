/**
 * Auth Context and Hook
 *
 * React context for authentication state management.
 */

import { createContext, useContext, useCallback, useEffect, useState, type ReactNode } from 'react';
import type { UserInfo } from '../api/auth';
import {
  login as apiLogin,
  verifyMFA as apiVerifyMFA,
  logout as apiLogout,
  refreshToken as apiRefreshToken,
  getCurrentUser,
  isMFARequired,
} from '../api/auth';

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
  login: (email: string, password: string) => Promise<{ mfaRequired: boolean; tempToken?: string }>;
  verifyMFA: (tempToken: string, code: string) => Promise<void>;
  logout: () => Promise<void>;
  refreshAuth: () => Promise<void>;
  canAccessTab: (tabId: string) => boolean;
  hasRole: (role: string) => boolean;
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
  logout: async () => {},
  refreshAuth: async () => {},
  canAccessTab: () => true,
  hasRole: () => false,
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

  // Load token from storage on mount
  useEffect(() => {
    const storedToken = sessionStorage.getItem(TOKEN_KEY);
    const storedExpiry = sessionStorage.getItem(TOKEN_EXPIRY_KEY);

    if (storedToken && storedExpiry) {
      const expiry = parseInt(storedExpiry, 10);
      if (expiry > Date.now()) {
        loadUser(storedToken);
        return;
      }
    }

    const handleUnauthorized = () => {
      setState((s) => ({
        ...s,
        isAuthenticated: false,
        user: null,
        accessToken: null,
      }));
      clearToken();
    };

    window.addEventListener('auth:unauthorized', handleUnauthorized);
    tryRefresh();

    return () => {
      window.removeEventListener('auth:unauthorized', handleUnauthorized);
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
    sessionStorage.setItem(TOKEN_KEY, token);
    sessionStorage.setItem(TOKEN_EXPIRY_KEY, expiry.toString());
  };

  const clearToken = () => {
    sessionStorage.removeItem(TOKEN_KEY);
    sessionStorage.removeItem(TOKEN_EXPIRY_KEY);
  };

  const login = useCallback(
    async (
      email: string,
      password: string
    ): Promise<{ mfaRequired: boolean; tempToken?: string }> => {
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
    },
    []
  );

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

  const canAccessTab = useCallback(
    (tabId: string): boolean => {
      if (!state.user) return true;
      if (!state.user.roles.includes('guest')) return true;
      if (state.user.allowed_tabs === null) return true;
      return state.user.allowed_tabs.includes(tabId);
    },
    [state.user]
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
        logout,
        refreshAuth,
        canAccessTab,
        hasRole,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}
