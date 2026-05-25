'use client';

import { useEffect, useState } from 'react';
import { usePathname } from 'next/navigation';
import { getSession } from '@/lib/auth';

const PUBLIC_PATHS = ['/login', '/onboarding', '/superuser-setup'];
const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? 'http://127.0.0.1:8765/api/v1';

function isPublic(pathname: string | null): boolean {
  if (!pathname) return false;
  return PUBLIC_PATHS.some((p) => pathname === p || pathname.startsWith(p + '/'));
}

export function AuthGuard({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [checked, setChecked] = useState(false);

  useEffect(() => {
    const s = getSession();
    if (s || isPublic(pathname)) {
      setChecked(true);
      return;
    }
    // No session and protected route. Check bootstrap status — if the
    // engine has no users yet we must route the user through the
    // SuperuserWizard, not the (useless) login page. fail-open on
    // probe error keeps the legacy /login path reachable.
    const ac = new AbortController();
    fetch(`${API_BASE}/auth/bootstrap/status`, { signal: ac.signal })
      .then((r) => (r.ok ? r.json() : null))
      .then((data: { needs_bootstrap?: boolean } | null) => {
        if (data?.needs_bootstrap) {
          window.location.replace('/superuser-setup');
        } else {
          window.location.replace('/login');
        }
      })
      .catch(() => {
        window.location.replace('/login');
      });
    return () => ac.abort();
  }, [pathname]);

  // Public pages: always render
  if (isPublic(pathname)) return <>{children}</>;

  // Protected: render only after auth check completed
  if (!checked) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-bg-canvas text-text-muted text-sm">
        Loading…
      </div>
    );
  }
  return <>{children}</>;
}
