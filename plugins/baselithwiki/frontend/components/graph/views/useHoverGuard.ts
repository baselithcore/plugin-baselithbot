import { useCallback, useEffect, useRef, useState, type RefObject } from 'react';

export type HoverMode = 'auto' | 'on' | 'off';

interface UseHoverGuardOptions {
  containerRef: RefObject<HTMLElement | null>;
  nodeCount: number;
  autoDisableAbove: number;
  delayMs?: number;
  cooldownMs?: number;
}

interface UseHoverGuardResult<TNode> {
  hoverId: string | null;
  onNodeHover: (node: TNode | null) => void;
  enabled: boolean;
  mode: HoverMode;
  setMode: (m: HoverMode) => void;
}

interface MinimalNode {
  id: string;
}

/**
 * Debounces + gates the hover state used to highlight neighborhoods in
 * force graphs. Why: react-force-graph fires `onNodeHover` on every frame
 * the raycaster picks a node, which on dense graphs causes constant
 * re-renders that disrupt camera/zoom. We add:
 *   - debounce: commit hover only after pointer rests `delayMs` on the same node
 *   - interaction-suppression: while user holds mouse / wheels / touches, hover
 *     is forced to null and updates are dropped; resumes after `cooldownMs`
 *   - auto-disable: on `auto` mode, large graphs (> threshold) skip hover entirely
 */
export function useHoverGuard<TNode extends MinimalNode>(
  opts: UseHoverGuardOptions
): UseHoverGuardResult<TNode> {
  const { containerRef, nodeCount, autoDisableAbove, delayMs = 120, cooldownMs = 220 } = opts;
  const [hoverId, setHoverId] = useState<string | null>(null);
  const [mode, setMode] = useState<HoverMode>('auto');

  const enabled = mode === 'on' || (mode === 'auto' && nodeCount <= autoDisableAbove);

  const interactingRef = useRef(false);
  const cooldownTimerRef = useRef<number | null>(null);
  const pendingTimerRef = useRef<number | null>(null);
  const pendingIdRef = useRef<string | null>(null);
  const lastCommittedRef = useRef<string | null>(null);

  const clearPending = useCallback(() => {
    if (pendingTimerRef.current !== null) {
      window.clearTimeout(pendingTimerRef.current);
      pendingTimerRef.current = null;
    }
  }, []);

  const commit = useCallback((id: string | null) => {
    if (lastCommittedRef.current === id) return;
    lastCommittedRef.current = id;
    setHoverId(id);
  }, []);

  const onNodeHover = useCallback(
    (node: TNode | null) => {
      if (!enabled) {
        if (lastCommittedRef.current !== null) commit(null);
        return;
      }
      if (interactingRef.current) {
        pendingIdRef.current = node ? node.id : null;
        return;
      }
      const id = node ? node.id : null;
      if (id === lastCommittedRef.current) {
        clearPending();
        return;
      }
      pendingIdRef.current = id;
      clearPending();
      if (id === null) {
        commit(null);
        return;
      }
      pendingTimerRef.current = window.setTimeout(() => {
        pendingTimerRef.current = null;
        if (interactingRef.current) return;
        commit(pendingIdRef.current);
      }, delayMs);
    },
    [enabled, delayMs, clearPending, commit]
  );

  useEffect(() => {
    if (!enabled && lastCommittedRef.current !== null) commit(null);
  }, [enabled, commit]);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    const startInteraction = () => {
      interactingRef.current = true;
      clearPending();
      if (lastCommittedRef.current !== null) commit(null);
      if (cooldownTimerRef.current !== null) {
        window.clearTimeout(cooldownTimerRef.current);
        cooldownTimerRef.current = null;
      }
    };
    const endInteraction = () => {
      if (cooldownTimerRef.current !== null) window.clearTimeout(cooldownTimerRef.current);
      cooldownTimerRef.current = window.setTimeout(() => {
        cooldownTimerRef.current = null;
        interactingRef.current = false;
      }, cooldownMs);
    };
    const onWheel = () => {
      startInteraction();
      endInteraction();
    };

    el.addEventListener('pointerdown', startInteraction);
    window.addEventListener('pointerup', endInteraction);
    window.addEventListener('pointercancel', endInteraction);
    el.addEventListener('wheel', onWheel, { passive: true });
    el.addEventListener('touchstart', startInteraction, { passive: true });
    window.addEventListener('touchend', endInteraction);

    return () => {
      el.removeEventListener('pointerdown', startInteraction);
      window.removeEventListener('pointerup', endInteraction);
      window.removeEventListener('pointercancel', endInteraction);
      el.removeEventListener('wheel', onWheel);
      el.removeEventListener('touchstart', startInteraction);
      window.removeEventListener('touchend', endInteraction);
      if (cooldownTimerRef.current !== null) window.clearTimeout(cooldownTimerRef.current);
      clearPending();
    };
  }, [containerRef, cooldownMs, clearPending, commit]);

  return { hoverId: enabled ? hoverId : null, onNodeHover, enabled, mode, setMode };
}
