/**
 * Auth Module Exports — context + API only.
 *
 * This barrel is dependency-free (React only) so any plugin can consume the
 * auth context via the `@auth` alias without inheriting the login UI's deps
 * (lucide-react, the auth stylesheet). The login wall (LoginPage,
 * ProtectedRoute) lives in the separate `@auth/login` entry (login.ts).
 */

// Context & Providers
export { AuthProvider, useAuth, AuthContext } from './hooks/useAuthContext';
export type { AuthState, AuthContextValue } from './hooks/useAuthContext';

// API
export * from './api/auth';
export type { UserInfo, TokenResponse, MFARequiredResponse } from './api/auth';
