'use client';

import { useEffect, useState } from 'react';
import { usePathname } from 'next/navigation';
import { getSession } from '@/lib/auth';

const PUBLIC_PATHS = ['/login', '/onboarding'];

function isPublic(pathname: string | null): boolean {
  if (!pathname) return false;
  return PUBLIC_PATHS.some((p) => pathname === p || pathname.startsWith(p + '/'));
}

export function AuthGuard({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [checked, setChecked] = useState(false);

  useEffect(() => {
    const s = getSession();
    if (!s && !isPublic(pathname)) {
      window.location.replace('/login');
      return;
    }
    setChecked(true);
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
