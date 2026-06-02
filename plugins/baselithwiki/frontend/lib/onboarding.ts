/**
 * Onboarding state — single namespace in localStorage.
 *
 * Hints, tour replays and version-bump modals all key off this module.
 * Server-side rendering returns safe defaults.
 */

const KEY_DISMISSED = 'onboarding.dismissed';
const KEY_LAST_SEEN_VERSION = 'onboarding.last_seen_version';

type Listener = () => void;
const listeners = new Set<Listener>();

function safeStorage(): Storage | null {
  try {
    if (typeof window === 'undefined') return null;
    return window.localStorage;
  } catch {
    return null;
  }
}

function readDismissedSet(): Set<string> {
  const s = safeStorage();
  if (!s) return new Set();
  try {
    const raw = s.getItem(KEY_DISMISSED);
    if (!raw) return new Set();
    const arr = JSON.parse(raw);
    return new Set(Array.isArray(arr) ? arr.filter((x) => typeof x === 'string') : []);
  } catch {
    return new Set();
  }
}

function writeDismissedSet(set: Set<string>): void {
  const s = safeStorage();
  if (!s) return;
  try {
    s.setItem(KEY_DISMISSED, JSON.stringify([...set]));
  } catch {
    /* quota or disabled — ignore */
  }
  listeners.forEach((l) => l());
}

export function isDismissed(id: string): boolean {
  return readDismissedSet().has(id);
}

export function dismiss(id: string): void {
  const set = readDismissedSet();
  if (set.has(id)) return;
  set.add(id);
  writeDismissedSet(set);
}

export function reset(id: string): void {
  const set = readDismissedSet();
  if (!set.delete(id)) return;
  writeDismissedSet(set);
}

export function resetAll(): void {
  writeDismissedSet(new Set());
}

export function listDismissed(): string[] {
  return [...readDismissedSet()];
}

export function lastSeenVersion(): string | null {
  const s = safeStorage();
  if (!s) return null;
  try {
    return s.getItem(KEY_LAST_SEEN_VERSION);
  } catch {
    return null;
  }
}

export function markVersionSeen(version: string): void {
  const s = safeStorage();
  if (!s) return;
  try {
    s.setItem(KEY_LAST_SEEN_VERSION, version);
  } catch {
    /* ignore */
  }
}

export function subscribe(listener: Listener): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}
