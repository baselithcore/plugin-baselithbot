"use client";

import { useEffect, useRef, useState } from "react";
import type { Finding, ChunkRow } from "@/lib/api";
import { cn } from "@/lib/cn";

interface Props {
  url: string;
  selected: Finding | null;
  chunks: ChunkRow[];
}

export function PdfCanvas({ url, selected, chunks }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [pageCount, setPageCount] = useState(0);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    let pdfDoc: {
      numPages: number;
      getPage: (n: number) => Promise<unknown>;
    } | null = null;

    (async () => {
      try {
        const pdfjs = await import("pdfjs-dist");
        // Worker loaded from CDN-free static path bundled by Next.js
        pdfjs.GlobalWorkerOptions.workerSrc = "/pdf.worker.min.mjs";
        const loadingTask = pdfjs.getDocument(url);
        pdfDoc = await loadingTask.promise;
        if (!pdfDoc || cancelled) return;
        setPageCount(pdfDoc.numPages);
        await renderAllPages(pdfDoc, containerRef.current);
      } catch (e) {
        setError(e instanceof Error ? e.message : "PDF render failed");
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [url]);

  useEffect(() => {
    if (!selected) return;
    const el = containerRef.current?.querySelector(
      `[data-chunk-id="${selected.evidence.chunk_id}"]`,
    );
    el?.scrollIntoView({ behavior: "smooth", block: "center" });
  }, [selected]);

  if (error) {
    return (
      <div className="p-6 text-sm text-status-danger">PDF error: {error}</div>
    );
  }

  return (
    <div ref={containerRef} className="space-y-4 p-4 bg-bg-canvas">
      {pageCount === 0 && (
        <p className="text-xs text-text-muted">Loading PDF…</p>
      )}
      {chunks.map((c) => {
        const highlighted = selected?.evidence.chunk_id === c.id;
        const sev = selected?.severity;
        return (
          <div
            key={c.id}
            data-chunk-id={c.id}
            className={cn(
              "absolute pointer-events-none transition-colors",
              highlighted &&
                sev === "FAIL" &&
                "bg-status-danger/15 outline outline-2 outline-status-danger/60",
              highlighted &&
                sev === "WARN" &&
                "bg-status-warning/15 outline outline-2 outline-status-warning/60",
              highlighted &&
                sev === "INFO" &&
                "bg-status-info/15 outline outline-2 outline-status-info/60",
            )}
            style={highlighted && c.bbox ? bboxStyle(c.bbox) : undefined}
          />
        );
      })}
    </div>
  );
}

function bboxStyle(bbox: string): React.CSSProperties {
  try {
    const [x0, y0, x1, y1] = JSON.parse(bbox) as [
      number,
      number,
      number,
      number,
    ];
    return { left: x0, top: y0, width: x1 - x0, height: y1 - y0 };
  } catch {
    return {};
  }
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
async function renderAllPages(pdfDoc: any, container: HTMLDivElement | null) {
  if (!container) return;
  for (let i = 1; i <= pdfDoc.numPages; i++) {
    const page = await pdfDoc.getPage(i);
    const viewport = page.getViewport({ scale: 1.4 });
    const canvas = document.createElement("canvas");
    canvas.width = viewport.width;
    canvas.height = viewport.height;
    canvas.className = "mx-auto shadow-md mb-4 rounded";
    const ctx = canvas.getContext("2d");
    if (!ctx) continue;
    container.appendChild(canvas);
    await page.render({ canvasContext: ctx, viewport }).promise;
  }
}
