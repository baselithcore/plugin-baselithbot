"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import {
  ChevronLeft,
  ChevronRight,
  FileText,
  LocateFixed,
  Search,
  ZoomIn,
  ZoomOut,
} from "lucide-react";
import { useAppStore } from "@/lib/store";
import { getChunks, type ChunkRow, type Finding } from "@/lib/api";
import { cn } from "@/lib/cn";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { EmptyState } from "@/components/ui/empty-state";
import { PageView } from "./PageView";

export function DocumentViewer() {
  const t = useTranslations("viewer");
  const docId = useAppStore((s) => s.currentDocId);
  const selected = useAppStore((s) => s.selectedFinding);
  const setSelected = useAppStore((s) => s.setSelectedFinding);
  const report = useAppStore((s) => s.currentReport);
  const containerRef = useRef<HTMLDivElement>(null);
  const [zoom, setZoom] = useState(100);
  const [query, setQuery] = useState("");

  const chunks = useQuery({
    queryKey: ["chunks", docId],
    queryFn: () => getChunks(docId!),
    enabled: !!docId,
  });

  const pages = useMemo(() => {
    const set = new Set<number>();
    (chunks.data ?? []).forEach((c) => {
      if (typeof c.page === "number") set.add(c.page);
    });
    return Array.from(set).sort((a, b) => a - b);
  }, [chunks.data]);

  const findingsByChunk = useMemo(() => {
    const m = new Map<string, Finding[]>();
    (report?.findings ?? []).forEach((f) => {
      const id = f.evidence.chunk_id;
      if (!id) return;
      const arr = m.get(id) ?? [];
      arr.push(f);
      m.set(id, arr);
    });
    return m;
  }, [report?.findings]);

  const chunksByPage = useMemo(() => {
    const m = new Map<number, ChunkRow[]>();
    (chunks.data ?? []).forEach((c) => {
      if (typeof c.page !== "number") return;
      const arr = m.get(c.page) ?? [];
      arr.push(c);
      m.set(c.page, arr);
    });
    m.forEach((arr) =>
      arr.sort((a, b) => (a.line_start ?? 0) - (b.line_start ?? 0)),
    );
    return m;
  }, [chunks.data]);

  const [pageIdx, setPageIdx] = useState(0);
  const currentPage = pages[pageIdx];

  useEffect(() => {
    if (pages.length && pageIdx >= pages.length) setPageIdx(0);
  }, [pages.length, pageIdx]);

  useEffect(() => {
    if (!selected) return;
    const targetPage = selected.evidence.page;
    if (typeof targetPage === "number") {
      const idx = pages.indexOf(targetPage);
      if (idx >= 0 && idx !== pageIdx) setPageIdx(idx);
    }
    const id = window.setTimeout(() => {
      const mark = containerRef.current?.querySelector(
        `[data-evidence-mark="${selected.evidence.chunk_id}"]`,
      );
      const fallback = containerRef.current?.querySelector(
        `[data-chunk-id="${selected.evidence.chunk_id}"]`,
      );
      (mark ?? fallback)?.scrollIntoView({
        behavior: "smooth",
        block: "center",
      });
    }, 80);
    return () => window.clearTimeout(id);
  }, [selected, pages, pageIdx]);

  if (!docId) {
    return (
      <div className="h-full bg-bg-panel-soft p-6">
        <EmptyState
          icon={FileText}
          title={t("noDocTitle")}
          description={t("noDocDesc")}
        />
      </div>
    );
  }

  const filteredChunks = (chunksByPage.get(currentPage ?? -1) ?? []).filter(
    (c) =>
      !query.trim() ? true : c.text.toLowerCase().includes(query.toLowerCase()),
  );

  const totalPages = pages.length || 1;
  const displayedPage = pages.length ? pageIdx + 1 : 1;
  const findingsThisPage = filteredChunks.reduce(
    (n, c) => n + (findingsByChunk.get(c.id)?.length ?? 0),
    0,
  );

  function gotoPrev() {
    if (pageIdx > 0) setPageIdx(pageIdx - 1);
  }
  function gotoNext() {
    if (pageIdx < pages.length - 1) setPageIdx(pageIdx + 1);
  }

  return (
    <TooltipProvider delayDuration={150}>
      <div className="h-full flex flex-col bg-bg-panel-soft">
        <Toolbar
          docId={docId}
          chunkCount={chunks.data?.length ?? 0}
          query={query}
          setQuery={setQuery}
          displayedPage={displayedPage}
          totalPages={totalPages}
          gotoPrev={gotoPrev}
          gotoNext={gotoNext}
          pageIdx={pageIdx}
          maxIdx={pages.length - 1}
          zoom={zoom}
          setZoom={setZoom}
          findingsCount={findingsThisPage}
          onLocate={() => {
            if (!selected) return;
            const el = containerRef.current?.querySelector(
              `[data-evidence-mark="${selected.evidence.chunk_id}"]`,
            ) as HTMLElement | null;
            (
              el ??
              containerRef.current?.querySelector(
                `[data-chunk-id="${selected.evidence.chunk_id}"]`,
              )
            )?.scrollIntoView({ behavior: "smooth", block: "center" });
          }}
        />

        <div className="flex flex-1 overflow-hidden">
          <div ref={containerRef} className="flex-1 overflow-auto">
            <div
              className="mx-auto max-w-3xl px-6 py-8"
              style={{ fontSize: `${zoom}%` }}
            >
              {chunks.isLoading && (
                <div className="space-y-3">
                  {Array.from({ length: 5 }).map((_, i) => (
                    <Skeleton key={i} className="h-20" />
                  ))}
                </div>
              )}

              {!chunks.isLoading && currentPage !== undefined && (
                <PageView
                  page={currentPage}
                  chunks={filteredChunks}
                  findingsByChunk={findingsByChunk}
                  selectedFinding={selected}
                  onSelectFinding={setSelected}
                  query={query}
                />
              )}

              {chunks.data && filteredChunks.length === 0 && (
                <p className="text-sm text-text-muted">{t("noMatch")}</p>
              )}

              {pages.length > 1 && (
                <div className="mt-6 flex items-center justify-between text-[11px] text-text-muted">
                  <button
                    type="button"
                    onClick={gotoPrev}
                    disabled={pageIdx <= 0}
                    className="inline-flex items-center gap-1 rounded-md border border-border bg-bg-canvas px-2 py-1.5 disabled:opacity-40"
                  >
                    <ChevronLeft size={12} /> {t("prevPage")}
                  </button>
                  <span className="font-mono tabular-nums">
                    {displayedPage} / {totalPages}
                  </span>
                  <button
                    type="button"
                    onClick={gotoNext}
                    disabled={pageIdx >= pages.length - 1}
                    className="inline-flex items-center gap-1 rounded-md border border-border bg-bg-canvas px-2 py-1.5 disabled:opacity-40"
                  >
                    {t("nextPage")} <ChevronRight size={12} />
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </TooltipProvider>
  );
}

interface ToolbarProps {
  docId: string;
  chunkCount: number;
  query: string;
  setQuery: (s: string) => void;
  displayedPage: number;
  totalPages: number;
  gotoPrev: () => void;
  gotoNext: () => void;
  pageIdx: number;
  maxIdx: number;
  zoom: number;
  setZoom: (fn: (z: number) => number) => void;
  findingsCount: number;
  onLocate: () => void;
}

function Toolbar({
  docId,
  chunkCount,
  query,
  setQuery,
  displayedPage,
  totalPages,
  gotoPrev,
  gotoNext,
  pageIdx,
  maxIdx,
  zoom,
  setZoom,
  findingsCount,
  onLocate,
}: ToolbarProps) {
  const t = useTranslations("viewer");
  return (
    <div className="h-12 border-b border-border bg-bg-panel/85 backdrop-blur-md px-3 flex items-center justify-between gap-3">
      <div className="flex min-w-0 items-center gap-2">
        <span className="flex h-8 w-8 items-center justify-center rounded-md border border-border bg-bg-canvas">
          <FileText size={15} className="text-status-info" />
        </span>
        <div className="min-w-0">
          <div className="truncate font-mono text-[11px] text-text-secondary">
            {docId}
          </div>
          <div className="text-[10px] uppercase tracking-wide text-text-muted">
            {t("stats", { chunks: chunkCount, findings: findingsCount })}
          </div>
        </div>
      </div>

      <label className="hidden md:flex h-8 w-[260px] items-center gap-2 rounded-md border border-border bg-bg-canvas px-2.5 text-xs">
        <Search size={12} className="text-text-muted" />
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder={t("search")}
          className="min-w-0 flex-1 bg-transparent outline-none placeholder:text-text-muted"
        />
        {query && (
          <button
            onClick={() => setQuery("")}
            className="text-[10px] text-text-muted hover:text-text-primary"
          >
            ×
          </button>
        )}
      </label>

      <div className="hidden items-center gap-1 md:flex">
        <ToolButton label={t("goToEvidence")} onClick={onLocate}>
          <LocateFixed size={14} />
        </ToolButton>
        <span className="mx-1 h-5 w-px bg-border" />
        <ToolButton
          label={t("prevPage")}
          onClick={gotoPrev}
          disabled={pageIdx <= 0}
        >
          <ChevronLeft size={14} />
        </ToolButton>
        <span className="px-2 font-mono text-[11px] text-text-muted tabular-nums">
          {displayedPage} / {totalPages}
        </span>
        <ToolButton
          label={t("nextPage")}
          onClick={gotoNext}
          disabled={pageIdx >= maxIdx}
        >
          <ChevronRight size={14} />
        </ToolButton>
        <span className="mx-1 h-5 w-px bg-border" />
        <ToolButton
          label={t("zoomOut")}
          onClick={() => setZoom((z) => Math.max(80, z - 10))}
        >
          <ZoomOut size={14} />
        </ToolButton>
        <span className="px-1.5 font-mono text-[11px] text-text-muted tabular-nums min-w-[36px] text-center">
          {zoom}%
        </span>
        <ToolButton
          label={t("zoomIn")}
          onClick={() => setZoom((z) => Math.min(150, z + 10))}
        >
          <ZoomIn size={14} />
        </ToolButton>
      </div>
    </div>
  );
}

function ToolButton({
  label,
  children,
  onClick,
  disabled,
}: {
  label: string;
  children: React.ReactNode;
  onClick?: () => void;
  disabled?: boolean;
}) {
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <button
          type="button"
          onClick={onClick}
          disabled={disabled}
          aria-label={label}
          className={cn(
            "inline-flex h-8 w-8 items-center justify-center rounded-md border border-border bg-bg-canvas transition-colors ring-focus",
            disabled
              ? "text-text-muted/50 cursor-not-allowed"
              : "text-text-secondary hover:bg-bg-panel-elev hover:text-text-primary",
          )}
        >
          {children}
        </button>
      </TooltipTrigger>
      <TooltipContent side="bottom">{label}</TooltipContent>
    </Tooltip>
  );
}
