import { useEffect, useState } from 'react';
import { fetchStatus } from '../lib/api';
import type { FeatureFlags } from '../lib/types';

const DEFAULT: FeatureFlags = {
  feedback_enabled: true,
};

/**
 * Feature flags esposti dal backend via `/api/status#features`.
 * Fallback ottimistico se il backend non è raggiungibile (UI abilitata);
 * l'effettivo invio fallirà silenziosamente nel submit e lo stato verrà
 * corretto al primo refresh riuscito.
 */
export function useFeatures(): FeatureFlags {
  const [flags, setFlags] = useState<FeatureFlags>(DEFAULT);
  useEffect(() => {
    const ctrl = new AbortController();
    fetchStatus(ctrl.signal)
      .then((s) => {
        if (s.features) setFlags({ ...DEFAULT, ...s.features });
      })
      .catch(() => {
        /* backend offline → default flags */
      });
    return () => ctrl.abort();
  }, []);
  return flags;
}
