import { useEffect, useState } from 'react';

/**
 * Ritorna ms trascorsi da `startedAt`. Si ferma a `stoppedAt` se passato, altrimenti
 * si aggiorna a ~10 Hz finché `running` è true.
 */
export function useElapsed(
  startedAt: number | undefined,
  running: boolean,
  stoppedAt?: number
): number {
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    if (!running || !startedAt) return;
    const id = window.setInterval(() => setNow(Date.now()), 100);
    return () => window.clearInterval(id);
  }, [running, startedAt]);

  if (!startedAt) return 0;
  const end = stoppedAt ?? (running ? now : startedAt);
  return Math.max(0, end - startedAt);
}
