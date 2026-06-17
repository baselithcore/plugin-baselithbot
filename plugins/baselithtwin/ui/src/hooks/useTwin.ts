// Central data hook: loads status, style, whitelist, facts, and the approval
// queue, and exposes mutators that re-fetch the affected slices. Kept framework-
// free (plain fetch + state) so the dashboard has no heavyweight data dependency.

import { useCallback, useEffect, useState } from 'react';
import { api } from '../api/client';
import type {
  AuditEvent,
  PendingReply,
  SalientFact,
  StyleProfile,
  TwinStatus,
  WhitelistEntry,
} from '../api/types';

export function useTwin() {
  const [status, setStatus] = useState<TwinStatus | null>(null);
  const [style, setStyle] = useState<StyleProfile | null>(null);
  const [whitelist, setWhitelist] = useState<WhitelistEntry[]>([]);
  const [facts, setFacts] = useState<SalientFact[]>([]);
  const [queue, setQueue] = useState<PendingReply[]>([]);
  const [audit, setAudit] = useState<AuditEvent[]>([]);
  const [error, setError] = useState<string | null>(null);

  const guard = useCallback(async (fn: () => Promise<void>) => {
    try {
      await fn();
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }, []);

  const refreshStatus = useCallback(
    () => guard(async () => setStatus(await api.status())),
    [guard]
  );
  const refreshStyle = useCallback(() => guard(async () => setStyle(await api.style())), [guard]);
  const refreshWhitelist = useCallback(
    () => guard(async () => setWhitelist(await api.whitelist())),
    [guard]
  );
  const refreshFacts = useCallback(() => guard(async () => setFacts(await api.facts())), [guard]);
  const refreshQueue = useCallback(
    () => guard(async () => setQueue(await api.replies(false))),
    [guard]
  );
  const refreshAudit = useCallback(() => guard(async () => setAudit(await api.audit(50))), [guard]);

  const refreshAll = useCallback(() => {
    void refreshStatus();
    void refreshStyle();
    void refreshWhitelist();
    void refreshFacts();
    void refreshQueue();
    void refreshAudit();
  }, [refreshStatus, refreshStyle, refreshWhitelist, refreshFacts, refreshQueue, refreshAudit]);

  useEffect(() => {
    refreshAll();
  }, [refreshAll]);

  const trainStyle = useCallback(
    () => guard(async () => setStyle(await api.trainStyle())),
    [guard]
  );
  const addWhitelist = useCallback(
    (id: string, name?: string) =>
      guard(async () => {
        await api.addWhitelist(id, name);
        await refreshWhitelist();
        await refreshStatus();
      }),
    [guard, refreshWhitelist, refreshStatus]
  );
  const removeWhitelist = useCallback(
    (id: string) =>
      guard(async () => {
        await api.removeWhitelist(id);
        await refreshWhitelist();
        await refreshStatus();
      }),
    [guard, refreshWhitelist, refreshStatus]
  );
  const decide = useCallback(
    (id: string, approve: boolean) =>
      guard(async () => {
        await (approve ? api.approve(id) : api.reject(id));
        await refreshQueue();
        await refreshStatus();
        await refreshAudit();
      }),
    [guard, refreshQueue, refreshStatus, refreshAudit]
  );
  const setPaused = useCallback(
    (paused: boolean) =>
      guard(async () => {
        await (paused ? api.pause() : api.resume());
        await refreshStatus();
        await refreshAudit();
      }),
    [guard, refreshStatus, refreshAudit]
  );

  return {
    status,
    style,
    whitelist,
    facts,
    queue,
    audit,
    error,
    refreshAll,
    refreshStatus,
    refreshQueue,
    refreshAudit,
    trainStyle,
    addWhitelist,
    removeWhitelist,
    decide,
    setPaused,
  };
}
