"use client";

import { useCallback, useState } from "react";
import { FileArchive, Loader2, ShieldCheck, Upload, X } from "lucide-react";
import { useMutation } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { uploadDocument, analyzeDocument } from "@/lib/api";
import { useAppStore } from "@/lib/store";
import { cn } from "@/lib/cn";
import { Progress } from "./ui/progress";

const ACCEPT = ".pdf,.docx,.xlsx,.md,.txt";
const MAX_BYTES = 50 * 1024 * 1024;

interface QueueItem {
  name: string;
  size: number;
  status: "pending" | "uploading" | "analyzing" | "done" | "error";
  message?: string;
}

export function Dropzone({ compact }: { compact?: boolean }) {
  const t = useTranslations("dropzone");
  const [drag, setDrag] = useState(false);
  const [items, setItems] = useState<QueueItem[]>([]);
  const setDocId = useAppStore((s) => s.setCurrentDocId);
  const setReport = useAppStore((s) => s.setCurrentReport);
  const policies = useAppStore((s) => s.selectedPolicies);

  const upload = useMutation({
    mutationFn: async (files: File[]) => {
      const initial: QueueItem[] = files.map((f) => ({
        name: f.name,
        size: f.size,
        status: "pending",
      }));
      setItems(initial);
      let lastReport = null;
      let lastId: string | null = null;
      for (let i = 0; i < files.length; i++) {
        const file = files[i];
        if (file.size > MAX_BYTES) {
          setItems((prev) =>
            prev.map((it, idx) =>
              idx === i
                ? { ...it, status: "error", message: t("exceedsMax") }
                : it,
            ),
          );
          continue;
        }
        try {
          setItems((prev) =>
            prev.map((it, idx) =>
              idx === i ? { ...it, status: "uploading" } : it,
            ),
          );
          const { id } = await uploadDocument(file);
          lastId = id;
          setItems((prev) =>
            prev.map((it, idx) =>
              idx === i ? { ...it, status: "analyzing" } : it,
            ),
          );
          const report = await analyzeDocument(id, policies);
          lastReport = report;
          setItems((prev) =>
            prev.map((it, idx) => (idx === i ? { ...it, status: "done" } : it)),
          );
        } catch (err) {
          const msg = err instanceof Error ? err.message : t("failed");
          setItems((prev) =>
            prev.map((it, idx) =>
              idx === i ? { ...it, status: "error", message: msg } : it,
            ),
          );
        }
      }
      if (lastId) setDocId(lastId);
      if (lastReport) setReport(lastReport);
    },
  });

  const onDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDrag(false);
      const files = Array.from(e.dataTransfer.files ?? []);
      if (files.length) upload.mutate(files);
    },
    [upload],
  );

  const busy = upload.isPending;

  return (
    <div className="space-y-3">
      <label
        onDragOver={(e) => {
          e.preventDefault();
          setDrag(true);
        }}
        onDragLeave={() => setDrag(false)}
        onDrop={onDrop}
        className={cn(
          "relative block cursor-pointer rounded-lg border border-dashed transition-colors duration-150 ease-smooth overflow-hidden",
          "bg-bg-panel-soft hover:bg-bg-panel",
          drag
            ? "border-status-info bg-status-info/10"
            : "border-border hover:border-status-info/50",
          compact ? "p-4" : "p-6",
        )}
      >
        {drag && (
          <div className="absolute inset-0 pointer-events-none animate-fade-in">
            <div className="absolute inset-0 bg-status-info/5" />
          </div>
        )}
        <div className="relative flex items-start gap-4">
          <div
            className={cn(
              "flex h-10 w-10 shrink-0 items-center justify-center rounded-md border transition-colors duration-150",
              drag
                ? "border-status-info/50 bg-status-info/20 text-status-info"
                : "border-status-info/30 bg-status-info/10 text-status-info",
            )}
          >
            {busy ? (
              <Loader2 className="w-5 h-5 animate-spin" />
            ) : (
              <Upload className="w-5 h-5" />
            )}
          </div>
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <p className="text-sm font-semibold">
                {busy ? t("processing") : drag ? t("release") : t("drop")}
              </p>
              <span className="rounded border border-border bg-bg-panel px-2 py-0.5 text-[10px] font-mono text-text-muted">
                {t("max")}
              </span>
            </div>
            <p className="mt-1 text-xs leading-5 text-text-muted">
              {t("formats")}
            </p>
            {!compact && (
              <div className="mt-4 grid gap-2 sm:grid-cols-2">
                <Trait icon={FileArchive} text={t("traitParsing")} />
                <Trait icon={ShieldCheck} text={t("traitSealing")} />
              </div>
            )}
          </div>
        </div>
        <input
          type="file"
          multiple
          accept={ACCEPT}
          className="sr-only"
          onChange={(e) => {
            const files = Array.from(e.target.files ?? []);
            if (files.length) upload.mutate(files);
          }}
          disabled={busy}
        />
      </label>

      {items.length > 0 && (
        <div className="rounded-lg border border-border bg-bg-panel-soft divide-y divide-border animate-slide-up mt-4">
          {items.map((it, i) => (
            <QueueRow key={i} item={it} />
          ))}
        </div>
      )}
    </div>
  );
}

function Trait({
  icon: Icon,
  text,
}: {
  icon: typeof FileArchive;
  text: string;
}) {
  return (
    <div className="flex items-center gap-2 rounded-md border border-border bg-bg-panel px-3 py-2 text-[11px] text-text-secondary">
      <Icon size={13} className="text-status-success" />
      {text}
    </div>
  );
}

function QueueRow({ item }: { item: QueueItem }) {
  const t = useTranslations("dropzone");
  const label =
    item.status === "done"
      ? t("statusAnalyzed")
      : item.status === "analyzing"
        ? t("statusAnalyzing")
        : item.status === "uploading"
          ? t("statusUploading")
          : item.status === "error"
            ? item.message || t("statusError")
            : t("statusQueued");
  return (
    <div className="flex items-center gap-3 px-3.5 py-2.5">
      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md border border-border bg-bg-panel text-text-muted">
        {item.status === "error" ? (
          <X size={14} className="text-status-danger" />
        ) : item.status === "done" ? (
          <ShieldCheck size={14} className="text-status-success" />
        ) : (
          <Loader2 size={14} className="animate-spin text-status-info" />
        )}
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex items-center justify-between gap-3">
          <span className="truncate text-xs font-medium">{item.name}</span>
          <span
            className={cn(
              "text-[10px] font-mono",
              item.status === "error"
                ? "text-status-danger"
                : item.status === "done"
                  ? "text-status-success"
                  : "text-text-muted",
            )}
          >
            {label}
          </span>
        </div>
        <Progress
          value={
            item.status === "done" ? 100 : item.status === "error" ? 100 : 60
          }
          tone={
            item.status === "error"
              ? "danger"
              : item.status === "done"
                ? "success"
                : "info"
          }
          indeterminate={
            item.status === "uploading" || item.status === "analyzing"
          }
          className="mt-1.5"
        />
      </div>
    </div>
  );
}
