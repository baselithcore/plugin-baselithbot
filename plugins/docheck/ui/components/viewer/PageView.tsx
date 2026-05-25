"use client";

import { useMemo } from "react";
import { cn } from "@/lib/cn";
import type { ChunkRow, Finding } from "@/lib/api";
import {
  EvidenceText,
  SEVERITY_TONE,
  renderWithQuery,
  resolveMatchRange,
} from "./highlight";

interface Props {
  page: number;
  chunks: ChunkRow[];
  findingsByChunk: Map<string, Finding[]>;
  selectedFinding: Finding | null;
  onSelectFinding: (f: Finding) => void;
  query: string;
}

const MIN_CHUNK_CHARS = 60;

export function PageView({
  page,
  chunks,
  findingsByChunk,
  selectedFinding,
  onSelectFinding,
  query,
}: Props) {
  const { totalFindings, hasFragmented } = useMemo(() => {
    let n = 0;
    let frag = 0;
    chunks.forEach((c) => {
      n += findingsByChunk.get(c.id)?.length ?? 0;
      if ((c.text?.length ?? 0) < MIN_CHUNK_CHARS) frag++;
    });
    return {
      totalFindings: n,
      hasFragmented: frag / Math.max(chunks.length, 1) > 0.4,
    };
  }, [chunks, findingsByChunk]);

  return (
    <article className="rounded-xl border border-slate-200 bg-white shadow-[0_1px_2px_rgba(15,23,42,0.04),0_4px_20px_-8px_rgba(15,23,42,0.08)]">
      <header className="sticky top-0 z-[1] flex items-center justify-between gap-3 rounded-t-xl border-b border-slate-200 bg-white/95 backdrop-blur px-6 py-3">
        <div className="flex items-center gap-3">
          <span className="inline-flex h-7 min-w-[2.25rem] items-center justify-center rounded-md border border-slate-300 bg-slate-50 px-2 font-mono text-[11px] font-semibold text-slate-700">
            P. {page}
          </span>
          <div className="text-[11px] text-slate-500">
            {chunks.length} sezioni
          </div>
        </div>
        {totalFindings > 0 && (
          <span className="text-[10px] font-medium uppercase tracking-wide text-slate-500">
            {totalFindings} finding
          </span>
        )}
      </header>

      <div className="px-6 py-6 sm:px-8">
        <ProseFlow
          chunks={chunks}
          findingsByChunk={findingsByChunk}
          selectedFinding={selectedFinding}
          onSelectFinding={onSelectFinding}
          query={query}
          compact={hasFragmented}
        />
      </div>
    </article>
  );
}

function ProseFlow({
  chunks,
  findingsByChunk,
  selectedFinding,
  onSelectFinding,
  query,
  compact,
}: {
  chunks: ChunkRow[];
  findingsByChunk: Map<string, Finding[]>;
  selectedFinding: Finding | null;
  onSelectFinding: (f: Finding) => void;
  query: string;
  compact: boolean;
}) {
  return (
    <div
      className={cn(
        "font-serif text-slate-800 leading-7",
        compact ? "text-[15px]" : "text-[14.5px]",
      )}
    >
      {chunks.map((c, idx) => {
        const findings = findingsByChunk.get(c.id) ?? [];
        const isSelected = selectedFinding?.evidence.chunk_id === c.id;
        const activeFinding =
          isSelected && selectedFinding
            ? selectedFinding
            : (findings[0] ?? null);
        const tone = activeFinding
          ? SEVERITY_TONE[activeFinding.severity]
          : null;

        // Compute highlight range from selected finding, OR fall back to the
        // first finding in the chunk so the offending span is visible even
        // before the user clicks the card.
        const findingForRange =
          isSelected && selectedFinding
            ? selectedFinding
            : (findings[0] ?? null);
        const range = findingForRange
          ? resolveMatchRange(c.text ?? "", findingForRange)
          : null;

        const hasFinding = findings.length > 0;
        const wrapAsBlock = hasFinding || isSelected;

        const body =
          findingForRange && range ? (
            <EvidenceText
              text={c.text ?? ""}
              range={range}
              chunkId={c.id}
              markCls={tone!.mark}
              mutedCls={tone!.mutedMark}
              active={isSelected}
              scrollOnMount={isSelected}
              query={query}
            />
          ) : (
            renderWithQuery(c.text ?? "", query)
          );

        if (wrapAsBlock) {
          return (
            <span
              key={c.id}
              data-chunk-id={c.id}
              className={cn(
                "scroll-m-20 my-1 inline-block w-full rounded-md px-3 py-2 align-baseline transition-colors",
                isSelected && tone?.band,
                !isSelected && hasFinding && tone?.band,
                !isSelected && hasFinding && "opacity-95",
              )}
            >
              {hasFinding && (
                <span className="mb-1 block">
                  {findings.map((f) => {
                    const t = SEVERITY_TONE[f.severity];
                    const sel = f.id === selectedFinding?.id;
                    return (
                      <button
                        key={f.id}
                        type="button"
                        onClick={() => onSelectFinding(f)}
                        title={f.explanation}
                        className={cn(
                          "mr-1.5 inline-flex items-center gap-1 rounded-full border px-1.5 py-0.5 text-[10px] font-sans font-medium transition-colors",
                          sel
                            ? `${t.badge} border-transparent`
                            : "border-slate-300 bg-white text-slate-600 hover:bg-slate-100",
                        )}
                      >
                        <span
                          className={cn(
                            "h-1.5 w-1.5 rounded-full",
                            sel ? "bg-white/90" : t.rail,
                          )}
                        />
                        {f.rule_id}
                      </button>
                    );
                  })}
                </span>
              )}
              <span className="whitespace-pre-wrap">{body}</span>
            </span>
          );
        }

        return (
          <span key={c.id} data-chunk-id={c.id} className="whitespace-pre-wrap">
            {body}
            {idx < chunks.length - 1 && needsSpace(c.text) ? " " : ""}
          </span>
        );
      })}
    </div>
  );
}

function needsSpace(text: string | null | undefined) {
  if (!text) return false;
  const last = text[text.length - 1];
  return !!last && !/\s/.test(last) && !/[—\-]/.test(last);
}
