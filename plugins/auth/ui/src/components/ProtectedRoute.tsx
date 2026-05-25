/**
 * Protected Route Component
 *
 * Wrapper that requires authentication to access children.
 */

import { type ReactNode } from 'react';
import { ShieldAlert } from 'lucide-react';
import { useAuth } from '../hooks/useAuthContext';
import LoginPage from './LoginPage';

interface ProtectedRouteProps {
  children: ReactNode;
  requiredRole?: string;
  requiredTab?: string;
}

export function ProtectedRoute({ children, requiredRole, requiredTab }: ProtectedRouteProps) {
  const { isAuthenticated, isLoading, hasRole, canAccessTab, user } = useAuth();

  if (isLoading) {
    return (
      <div className="auth-loading">
        <div className="auth-spinner-large" />
        <p>Loading...</p>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <LoginPage />;
  }

  if (requiredRole && !hasRole(requiredRole)) {
    return (
      <div className="auth-forbidden">
        <ShieldAlert size={64} className="auth-forbidden-icon" />
        <h1>Access Denied</h1>
        <p>You don't have permission to access this page.</p>
        <p className="auth-forbidden-detail">
          Required role: <code>{requiredRole}</code>
        </p>
      </div>
    );
  }

  if (requiredTab && !canAccessTab(requiredTab)) {
    return (
      <div className="auth-forbidden">
        <ShieldAlert size={64} className="auth-forbidden-icon" />
        <h1>Access Denied</h1>
        <p>You don't have access to this section.</p>
        {user?.allowed_tabs && (
          <p className="auth-forbidden-detail">
            Your access is limited to: {user.allowed_tabs.join(', ')}
          </p>
        )}
      </div>
    );
  }

  return <>{children}</>;
}

/**
 * Hook for conditional rendering based on auth.
 */
export function useProtectedContent(requiredRole?: string, requiredTab?: string) {
  const { isAuthenticated, hasRole, canAccessTab } = useAuth();

  const isAllowed =
    isAuthenticated &&
    (!requiredRole || hasRole(requiredRole)) &&
    (!requiredTab || canAccessTab(requiredTab));

  return { isAllowed };
}
