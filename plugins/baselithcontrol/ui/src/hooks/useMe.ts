import { useEffect } from 'react';
import { fetchMe } from '@/lib/api';
import { useControlStore } from '@/store/useControlStore';

// Resolve the caller's identity once so the UI can gate privileged controls.
// On failure (e.g. 401 when auth is enforced and the user is not logged in) the
// caller is treated as non-admin.
export function useMe(): void {
  const setMe = useControlStore((s) => s.setMe);
  useEffect(() => {
    let alive = true;
    fetchMe()
      .then((me) => alive && setMe(me))
      .catch(() => alive && setMe(null));
    return () => {
      alive = false;
    };
  }, [setMe]);
}
