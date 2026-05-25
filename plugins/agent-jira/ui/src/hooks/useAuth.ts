import { useState, useEffect, useCallback } from 'react';
import {
  authLogin,
  authRegister,
  authMe,
  getStoredToken,
  setStoredToken,
  clearStoredToken,
} from '../api/client';
import type { AuthUser } from '../types';

export type AuthState = {
  user: AuthUser | null;
  maxUsers: number;
  loading: boolean;
  error: string | null;
};

export function useAuth() {
  const [state, setState] = useState<AuthState>(() => {
    const token = getStoredToken();
    return {
      user: null,
      maxUsers: 1,
      loading: !!token,
      error: null,
    };
  });

  // Check existing token on mount
  useEffect(() => {
    const token = getStoredToken();
    if (!token) return;

    authMe()
      .then((res) => {
        setState({ user: res.user, maxUsers: res.max_users ?? 1, loading: false, error: null });
      })
      .catch(() => {
        clearStoredToken();
        setState({ user: null, maxUsers: 1, loading: false, error: null });
      });
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    setState((s) => ({ ...s, loading: true, error: null }));
    try {
      const res = await authLogin({ email, password });
      setStoredToken(res.token);
      setState((s) => ({ ...s, user: res.user, loading: false, error: null }));
      return res.user;
    } catch (err: any) {
      const message = err.message || 'Errore durante il login.';
      setState((s) => ({ ...s, loading: false, error: message }));
      throw err;
    }
  }, []);

  const register = useCallback(
    async (email: string, password: string, displayName?: string, organization?: string) => {
      setState((s) => ({ ...s, loading: true, error: null }));
      try {
        await authRegister({
          email,
          password,
          display_name: displayName,
          organization,
        });
        // Don't auto-login — let the user confirm via login form
        setState((s) => ({ ...s, loading: false, error: null }));
        return true;
      } catch (err: any) {
        const message = err.message || 'Errore durante la registrazione.';
        setState((s) => ({ ...s, loading: false, error: message }));
        throw err;
      }
    },
    []
  );

  const logout = useCallback(() => {
    clearStoredToken();
    setState({ user: null, maxUsers: 1, loading: false, error: null });
  }, []);

  return {
    user: state.user,
    maxUsers: state.maxUsers,
    loading: state.loading,
    error: state.error,
    login,
    register,
    logout,
    isAuthenticated: !!state.user,
  };
}
