'use client';

import { cn } from '@/lib/cn';
import type { Finding } from '@/lib/api';

export const SEVERITY_TONE = {
  FAIL: {
    band: 'bg-red-50 border-l-2 border-red-400',
    rail: 'bg-red-500',
    mark: 'bg-red-200/95 text-red-950 ring-2 ring-red-500/70 shadow-[0_0_0_4px_rgba(239,68,68,0.12)]',
    mutedMark:
      'bg-red-100/70 text-red-900 ring-1 ring-red-400/40 underline decoration-red-400/60 decoration-2 underline-offset-2',
    badge: 'bg-red-600 text-white',
  },
  WARN: {
    band: 'bg-amber-50 border-l-2 border-amber-400',
    rail: 'bg-amber-500',
    mark: 'bg-amber-200/95 text-amber-950 ring-2 ring-amber-500/70 shadow-[0_0_0_4px_rgba(245,158,11,0.12)]',
    mutedMark:
      'bg-amber-100/70 text-amber-900 ring-1 ring-amber-400/40 underline decoration-amber-400/60 decoration-2 underline-offset-2',
    badge: 'bg-amber-600 text-white',
  },
  PASS: {
    band: 'bg-emerald-50 border-l-2 border-emerald-400',
    rail: 'bg-emerald-500',
    mark: 'bg-emerald-200/95 text-emerald-950 ring-2 ring-emerald-500/70 shadow-[0_0_0_4px_rgba(16,185,129,0.12)]',
    mutedMark: 'bg-emerald-100/70 text-emerald-900 ring-1 ring-emerald-400/40',
    badge: 'bg-emerald-600 text-white',
  },
  INFO: {
    band: 'bg-sky-50 border-l-2 border-sky-400',
    rail: 'bg-sky-500',
    mark: 'bg-sky-200/95 text-sky-950 ring-2 ring-sky-500/70 shadow-[0_0_0_4px_rgba(14,165,233,0.12)]',
    mutedMark:
      'bg-sky-100/70 text-sky-900 ring-1 ring-sky-400/40 underline decoration-sky-400/60 decoration-2 underline-offset-2',
    badge: 'bg-sky-600 text-white',
  },
} as const;

/** Extract candidate quote phrases from finding metadata (best to worst). */
function candidateQuotes(finding: Finding): string[] {
  const out: string[] = [];
  const ev = finding.evidence;
  if (ev.snippet) out.push(ev.snippet);
  // Quoted phrases inside explanation: 'scadenza', "due date", «foo».
  const re = /['"«»“”‘’]([^'"«»“”‘’]{2,80})['"«»“”‘’]/g;
  for (const m of finding.explanation?.matchAll(re) ?? []) {
    if (m[1]) out.push(m[1]);
  }
  // Policy excerpt as last resort (often longer than chunk fragment, but
  // its first 4-5 words may exist verbatim).
  const ex = finding.policy_ref.excerpt?.trim();
  if (ex) {
    const head = ex.split(/\s+/).slice(0, 5).join(' ');
    if (head.length >= 8) out.push(head);
  }
  return out;
}

function locateLoose(text: string, needle: string): [number, number] | null {
  if (!needle) return null;
  let idx = text.indexOf(needle);
  if (idx >= 0) return [idx, idx + needle.length];
  idx = text.toLowerCase().indexOf(needle.toLowerCase());
  if (idx >= 0) return [idx, idx + needle.length];
  return null;
}

export function resolveMatchRange(text: string, finding: Finding | null): [number, number] | null {
  if (!finding || !text) return null;
  const ev = finding.evidence;
  if (
    typeof ev.match_start === 'number' &&
    typeof ev.match_end === 'number' &&
    ev.match_end > ev.match_start &&
    ev.match_end <= text.length
  ) {
    return [ev.match_start, ev.match_end];
  }
  for (const q of candidateQuotes(finding)) {
    const r = locateLoose(text, q);
    if (r) return r;
  }
  return null;
}

import { useEffect, useRef } from 'react';

export function EvidenceText({
  text,
  range,
  chunkId,
  markCls,
  query,
  active = true,
  scrollOnMount = false,
  mutedCls,
}: {
  text: string;
  range: [number, number];
  chunkId: string;
  markCls: string;
  query: string;
  /** Active mark gets full ring + pulse. Inactive gets subdued tint. */
  active?: boolean;
  /** Scroll mark into view on mount (used when finding selected). */
  scrollOnMount?: boolean;
  /** Class applied when not active (severity-tinted muted highlight). */
  mutedCls?: string;
}) {
  const [s, e] = range;
  const markRef = useRef<HTMLElement | null>(null);
  useEffect(() => {
    if (scrollOnMount && markRef.current) {
      markRef.current.scrollIntoView({ block: 'center', behavior: 'smooth' });
    }
  }, [scrollOnMount, s, e]);
  return (
    <>
      {renderWithQuery(text.slice(0, s), query)}
      <mark
        ref={(el) => {
          markRef.current = el;
        }}
        data-evidence-mark={chunkId}
        aria-current={active ? 'true' : undefined}
        className={cn(
          'rounded px-1 py-0.5 font-medium transition-all duration-300',
          active
            ? `animate-evidence-pulse ${markCls}`
            : (mutedCls ?? 'bg-amber-100/60 text-amber-900 ring-1 ring-amber-400/40')
        )}
      >
        {text.slice(s, e)}
      </mark>
      {renderWithQuery(text.slice(e), query)}
    </>
  );
}

export function renderWithQuery(text: string, query: string) {
  if (!query.trim()) return text;
  const parts = text.split(new RegExp(`(${query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi'));
  return parts.map((part, i) =>
    part.toLowerCase() === query.toLowerCase() ? (
      <mark key={i} className="rounded px-0.5 bg-yellow-200/80 text-slate-900">
        {part}
      </mark>
    ) : (
      <span key={i}>{part}</span>
    )
  );
}
