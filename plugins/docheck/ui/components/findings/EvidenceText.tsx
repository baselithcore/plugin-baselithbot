"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useTranslations } from "next-intl";
import { cn } from "@/lib/cn";
import type { Citation } from "@/lib/api";

interface Props {
  evidence: Citation;
  /** Optional fallback quote when match offsets are absent (e.g. pull from
   * explanation or rule excerpt). */
  fallbackQuote?: string;
}

interface Span {
  start: number;
  end: number;
}

const CONTEXT_PAD = 240; // chars of context shown around the match by default

/** Locate `needle` in `haystack`. Tries strict, case-insensitive, then
 * whitespace-tolerant. Returns char offsets in original `haystack`. */
function locate(haystack: string, needle: string): Span | null {
  if (!needle || !haystack) return null;
  let idx = haystack.indexOf(needle);
  if (idx >= 0) return { start: idx, end: idx + needle.length };
  const lh = haystack.toLowerCase();
  const ln = needle.toLowerCase();
  idx = lh.indexOf(ln);
  if (idx >= 0) return { start: idx, end: idx + needle.length };
  // Whitespace-tolerant scan
  const norm = needle.trim().toLowerCase().replace(/\s+/g, " ");
  if (!norm) return null;
  for (let i = 0; i < haystack.length; i++) {
    let j = i;
    let k = 0;
    while (j < haystack.length && k < norm.length) {
      const ch = haystack[j].toLowerCase();
      const nc = norm[k];
      if (/\s/.test(ch) && nc === " ") {
        while (j < haystack.length && /\s/.test(haystack[j])) j++;
        k++;
        continue;
      }
      if (ch === nc) {
        j++;
        k++;
        continue;
      }
      break;
    }
    if (k === norm.length) return { start: i, end: j };
  }
  return null;
}

export function EvidenceText({ evidence, fallbackQuote }: Props) {
  const t = useTranslations("findings.detail");
  const text = evidence.text || "";
  const markRef = useRef<HTMLElement | null>(null);
  const [expanded, setExpanded] = useState(false);

  const span = useMemo<Span | null>(() => {
    if (
      typeof evidence.match_start === "number" &&
      typeof evidence.match_end === "number" &&
      evidence.match_end > evidence.match_start &&
      evidence.match_end <= text.length
    ) {
      return { start: evidence.match_start, end: evidence.match_end };
    }
    if (fallbackQuote) {
      const located = locate(text, fallbackQuote);
      if (located) return located;
    }
    return null;
  }, [evidence.match_start, evidence.match_end, text, fallbackQuote]);

  // Determine visible window: match + context, unless expanded.
  const window = useMemo(() => {
    if (!span || expanded)
      return { start: 0, end: text.length, truncated: false };
    const start = Math.max(0, span.start - CONTEXT_PAD);
    const end = Math.min(text.length, span.end + CONTEXT_PAD);
    return {
      start,
      end,
      truncated: start > 0 || end < text.length,
    };
  }, [span, expanded, text.length]);

  // Auto-scroll the highlight into view on mount/change.
  useEffect(() => {
    if (markRef.current) {
      markRef.current.scrollIntoView({ block: "center", behavior: "smooth" });
    }
  }, [span?.start, span?.end, expanded]);

  if (!text) return null;

  // No match found: render plain text (no highlight).
  if (!span) {
    return (
      <div className="space-y-1">
        <blockquote
          className={cn(
            "rounded border-l-2 border-status-info/40 bg-bg-panel-soft px-3 py-2 text-[12px] leading-5 text-text-secondary",
            "max-h-72 overflow-auto whitespace-pre-wrap",
          )}
        >
          {text}
        </blockquote>
        <div className="text-[10px] text-text-faint">{t("noMatchHint")}</div>
      </div>
    );
  }

  const before = text.slice(window.start, span.start);
  const matched = text.slice(span.start, span.end);
  const after = text.slice(span.end, window.end);

  return (
    <div className="space-y-2">
      <blockquote
        className={cn(
          "rounded border-l-2 border-status-warning/60 bg-bg-panel-soft px-3 py-2 text-[12px] leading-5 text-text-secondary",
          "max-h-72 overflow-auto whitespace-pre-wrap",
        )}
      >
        {window.start > 0 && <span className="text-text-faint">…</span>}
        {before}
        <mark
          ref={(el) => {
            markRef.current = el;
          }}
          className="rounded-[2px] bg-status-warning/30 px-0.5 text-text-primary ring-1 ring-status-warning/50"
        >
          {matched}
        </mark>
        {after}
        {window.end < text.length && <span className="text-text-faint">…</span>}
      </blockquote>
      <div className="flex items-center justify-between text-[10px] text-text-muted">
        <span>{t("matchOffset", { start: span.start, end: span.end })}</span>
        {window.truncated && (
          <button
            type="button"
            onClick={() => setExpanded((v) => !v)}
            className="underline decoration-dotted text-status-info hover:text-status-info/80"
          >
            {expanded ? t("collapseContext") : t("expandContext")}
          </button>
        )}
      </div>
    </div>
  );
}
