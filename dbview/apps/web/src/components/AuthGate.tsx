import { useEffect, useState, type ReactNode } from 'react';
import { Loader2 } from 'lucide-react';
import { bootstrapSession, getCurrentUser, subscribe } from '../lib/auth.js';
import { GATEWAY_AUTH } from '../lib/runtime-config.js';
import { GatewayLoginNotice } from './GatewayLoginNotice.js';
import { LoginPage } from './LoginPage.js';
import { ChangePasswordPage } from './ChangePasswordPage.js';

interface Props {
  children: ReactNode;
}

export function AuthGate({ children }: Props) {
  const [ready, setReady] = useState(false);
  const [user, setUser] = useState(getCurrentUser());

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

  if (!user) {
    if (GATEWAY_AUTH) {
      return <GatewayLoginNotice />;
    }
    return <LoginPage onAuthenticated={() => setUser(getCurrentUser())} />;
  }

  if (user.mustChangePassword) {
    return <ChangePasswordPage email={user.email} onChanged={() => setUser(getCurrentUser())} />;
  }

  return <>{children}</>;
}
