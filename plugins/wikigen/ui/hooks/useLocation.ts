/**
 * Minimal pathname-based router. No deps. Sync con popstate + custom
 * `app:navigate` event per propagare push interni a tutti gli ascoltatori.
 */
import { useCallback, useEffect, useState } from 'react';

const NAV_EVENT = 'app:navigate';

export function navigate(to: string, replace = false): void {
  if (typeof window === 'undefined') return;
  if (replace) window.history.replaceState({}, '', to);
  else window.history.pushState({}, '', to);
  window.dispatchEvent(new CustomEvent(NAV_EVENT));
}

export function useLocation(): { path: string; navigate: typeof navigate } {
  const [path, setPath] = useState(() =>
    typeof window === 'undefined' ? '/' : window.location.pathname
  );
  useEffect(() => {
    const sync = () => setPath(window.location.pathname);
    window.addEventListener('popstate', sync);
    window.addEventListener(NAV_EVENT, sync);
    return () => {
      window.removeEventListener('popstate', sync);
      window.removeEventListener(NAV_EVENT, sync);
    };
  }, []);
  const nav = useCallback((to: string, replace = false) => {
    navigate(to, replace);
  }, []);
  return { path, navigate: nav };
}
