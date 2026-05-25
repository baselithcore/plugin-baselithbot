import { useCallback, useEffect, useState, type ReactNode } from 'react';
import { Loader2 } from 'lucide-react';
import { bootstrapSession, getCurrentUser, subscribe } from '../lib/auth.js';
import { LoginPage } from './LoginPage.js';
import { ChangePasswordPage } from './ChangePasswordPage.js';
import { SuperuserWizard } from './SuperuserWizard.js';

interface Props {
  children: ReactNode;
}

export function AuthGate({ children }: Props) {
  const [ready, setReady] = useState(false);
  const [user, setUser] = useState(getCurrentUser());
  // First-boot gate. The wizard self-checks /auth/bootstrap/status and
  // resolves to onComplete (sets false) either when bootstrap is not
  // needed or after a successful submit. Mounted only when there is
  // no session, so refreshed pages always go through the wizard before
  // hitting LoginPage on a fresh install.
  const [bootstrapPending, setBootstrapPending] = useState(true);
  const onBootstrapComplete = useCallback(() => {
    setBootstrapPending(false);
    setUser(getCurrentUser());
  }, []);

  useEffect(() => {
    let mounted = true;
    bootstrapSession().finally(() => {
      if (!mounted) return;
      setUser(getCurrentUser());
      setReady(true);
    });
    const unsub = subscribe(() => setUser(getCurrentUser()));
    return () => {
      mounted = false;
      unsub();
    };
  }, []);

  if (!ready) {
    return (
      <div className="h-screen w-screen flex items-center justify-center bg-surface-0 text-text-muted">
        <Loader2 className="w-5 h-5 animate-spin" aria-label="Loading session" />
      </div>
    );
  }

  if (!user && bootstrapPending) {
    return <SuperuserWizard onComplete={onBootstrapComplete} />;
  }

  if (!user) {
    return <LoginPage onAuthenticated={() => setUser(getCurrentUser())} />;
  }

  if (user.mustChangePassword) {
    return <ChangePasswordPage email={user.email} onChanged={() => setUser(getCurrentUser())} />;
  }

  return <>{children}</>;
}
