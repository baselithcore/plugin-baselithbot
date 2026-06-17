import { useCallback, useEffect, useState } from 'react';
import { api, subscribeRecommendations } from '../api';
import type { Recommendation, Scenario, Status, Stint } from '../types';

/** Owns all live pit-wall data: status/cars polling, the selected-car stint,
 * the SSE recommendation stream, and on-demand scenario simulation. */
export function usePitwall() {
  const [status, setStatus] = useState<Status | null>(null);
  const [cars, setCars] = useState<string[]>([]);
  const [car, setCar] = useState<string | null>(null);
  const [stint, setStint] = useState<Stint | null>(null);
  const [recs, setRecs] = useState<Recommendation[]>([]);
  const [scenario, setScenario] = useState<Scenario | null>(null);
  const [busy, setBusy] = useState(false);
  const [session, setSession] = useState('demo');

  // Status + car roster on a 1s cadence.
  useEffect(() => {
    let alive = true;
    const tick = async () => {
      try {
        const s = await api.status();
        if (!alive) return;
        setStatus(s);
        const c = await api.cars();
        if (!alive) return;
        setCars(c);
        setCar((prev) => prev ?? c[0] ?? null);
      } catch {
        /* backend warming up */
      }
    };
    void tick();
    const id = setInterval(tick, 1000);
    return () => {
      alive = false;
      clearInterval(id);
    };
  }, []);

  // Selected-car stint telemetry.
  useEffect(() => {
    if (!car) return;
    let alive = true;
    const tick = async () => {
      try {
        const s = await api.stint(car);
        if (alive) setStint(s);
      } catch {
        /* no stint yet */
      }
    };
    void tick();
    const id = setInterval(tick, 1000);
    return () => {
      alive = false;
      clearInterval(id);
    };
  }, [car]);

  // Live recommendation stream + backfill; resets on session change.
  useEffect(() => {
    setRecs([]);
    setCar(null);
    void api
      .recommendations()
      .then(setRecs)
      .catch(() => undefined);
    return subscribeRecommendations((rec) => setRecs((prev) => [rec, ...prev].slice(0, 60)));
  }, [session]);

  const simulate = useCallback(async () => {
    if (!car) return;
    setBusy(true);
    try {
      setScenario(await api.simulate(car));
    } catch {
      setScenario(null);
    } finally {
      setBusy(false);
    }
  }, [car]);

  const signals = recs.find((r) => r.car_id === car)?.pheromone_signals ?? {};

  return {
    status,
    cars,
    car,
    setCar,
    stint,
    recs,
    scenario,
    busy,
    simulate,
    signals,
    session,
    setSession,
  };
}
