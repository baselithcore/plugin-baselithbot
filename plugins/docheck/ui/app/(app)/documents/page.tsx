"use client";

import { useMemo, useState } from "react";
import {
  useMutation,
  useQuery,
  useQueryClient,
  keepPreviousData,
} from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { useTranslations } from "next-intl";
import {
  ChevronLeft,
  ChevronRight,
  Clock,
  Database,
  Download,
  FileText,
  Loader2,
  Play,
  Search,
  ShieldCheck,
  Trash2,
} from "lucide-react";
import { TopBar } from "@/components/TopBar";
import { Dropzone } from "@/components/Dropzone";
import { PageHeader } from "@/components/PageHeader";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import { Button } from "@/components/ui/button";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import {
  analyzeDocument,
  deleteDocument,
  downloadDocument,
  listDocumentsPage,
  type DocumentRow,
} from "@/lib/api";
import { useAppStore } from "@/lib/store";
import { cn } from "@/lib/cn";

const PAGE_SIZE = 25;

const STATUS_FILTERS: {
  value: string;
  i18nKey: "all" | "uploaded" | "parsed" | "indexed" | "failed";
}[] = [
  { value: "all", i18nKey: "all" },
  { value: "uploaded", i18nKey: "uploaded" },
  { value: "parsed", i18nKey: "parsed" },
  { value: "indexed", i18nKey: "indexed" },
  { value: "failed", i18nKey: "failed" },
];

function relativeTime(iso: string): string {
  const diff = (Date.now() - new Date(iso).getTime()) / 1000;
  if (diff < 60) return `${Math.floor(diff)}s ago`;
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
}

function statusTone(status: string): { fg: string; bd: string; bg: string } {
  switch (status) {
    case "failed":
      return {
        fg: "text-status-danger",
        bd: "border-status-danger/30",
        bg: "bg-status-danger/10",
      };
    case "uploaded":
      return {
        fg: "text-status-warning",
        bd: "border-status-warning/30",
        bg: "bg-status-warning/10",
      };
    case "parsed":
    case "indexed":
      return {
        fg: "text-status-success",
        bd: "border-status-success/30",
        bg: "bg-status-success/10",
      };
    default:
      return { fg: "text-text-muted", bd: "border-border", bg: "bg-bg-panel" };
  }
}

function scoreTone(score: number): string {
  if (score >= 80) return "text-status-success";
  if (score >= 60) return "text-status-warning";
  return "text-status-danger";
}

export default function DocumentsPage() {
  const t = useTranslations("documents");
  const router = useRouter();
  const qc = useQueryClient();
  const setDocId = useAppStore((s) => s.setCurrentDocId);
  const setReport = useAppStore((s) => s.setCurrentReport);
  const policies = useAppStore((s) => s.selectedPolicies);

  const [query, setQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [page, setPage] = useState(0);
  const [confirmDel, setConfirmDel] = useState<DocumentRow | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);

  const params = useMemo(
    () => ({
      limit: PAGE_SIZE,
      offset: page * PAGE_SIZE,
      q: query.trim() || undefined,
      status: statusFilter === "all" ? undefined : [statusFilter],
    }),
    [page, query, statusFilter],
  );

  const docs = useQuery({
    queryKey: ["documents", params],
    queryFn: () => listDocumentsPage(params),
    placeholderData: keepPreviousData,
  });

  const rows = docs.data?.rows ?? [];
  const total = docs.data?.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const totalSize = rows.reduce((s, d) => s + d.size_bytes, 0);

  const analyzeMut = useMutation({
    mutationFn: (docId: string) => analyzeDocument(docId, policies),
  });

  const deleteMut = useMutation({
    mutationFn: (docId: string) => deleteDocument(docId),
    onSuccess: () => {
      toast.success(t("toastDeleted"));
      qc.invalidateQueries({ queryKey: ["documents"] });
      qc.invalidateQueries({ queryKey: ["workspace"] });
    },
    onError: (e) =>
      toast.error(e instanceof Error ? e.message : t("toastDeleteFailed")),
  });

  function open(d: DocumentRow) {
    setDocId(d.id);
    setReport(null);
    if (d.latest_report) {
      router.push(`/?doc=${d.id}&report=${d.latest_report.report_id}`);
    } else {
      router.push(`/?doc=${d.id}`);
    }
  }

  async function runAnalyze(d: DocumentRow) {
    setBusyId(d.id);
    const tid = toast.loading(t("toastAnalyzing", { name: d.filename }));
    try {
      const report = await analyzeMut.mutateAsync(d.id);
      setDocId(d.id);
      setReport(report);
      toast.success(t("toastAnalysisDone", { score: report.score }), {
        id: tid,
      });
      qc.invalidateQueries({ queryKey: ["documents"] });
      qc.invalidateQueries({ queryKey: ["workspace"] });
      router.push(`/?doc=${d.id}&report=${report.report_id}`);
    } catch (e) {
      toast.error(e instanceof Error ? e.message : t("toastAnalysisFailed"), {
        id: tid,
      });
    } finally {
      setBusyId(null);
    }
  }

  async function runDownload(d: DocumentRow) {
    setBusyId(d.id);
    try {
      await downloadDocument(d.id, d.filename);
    } catch (e) {
      toast.error(e instanceof Error ? e.message : t("toastDownloadFailed"));
    } finally {
      setBusyId(null);
    }
  }

  function viewReport(d: DocumentRow) {
    if (!d.latest_report) return;
    setDocId(d.id);
    setReport(null);
    router.push(`/?doc=${d.id}&report=${d.latest_report.report_id}`);
  }

  function onSearchChange(v: string) {
    setPage(0);
    setQuery(v);
  }

  function onStatusChange(v: string) {
    setPage(0);
    setStatusFilter(v);
  }

  return (
    <div className="h-screen flex flex-col">
      <TopBar />
      <main className="flex-1 overflow-auto p-6">
        <div className="mx-auto max-w-7xl">
          <PageHeader
            eyebrow={t("eyebrow")}
            eyebrowIcon={Database}
            title={t("title")}
            description={t("description")}
            actions={
              <label className="flex h-10 items-center gap-2 rounded-md border border-border bg-bg-panel px-3 text-xs text-text-muted w-full lg:w-[360px]">
                <Search size={14} />
                <input
                  value={query}
                  onChange={(e) => onSearchChange(e.target.value)}
                  placeholder={t("search")}
                  className="min-w-0 flex-1 bg-transparent outline-none text-text-primary placeholder:text-text-muted"
                />
              </label>
            }
          />

          <div className="mb-5 grid gap-3 md:grid-cols-3">
            <VaultMetric label={t("metricTotal")} value={String(total)} />
            <VaultMetric
              label={t("metricPageSize")}
              value={`${(totalSize / 1024 / 1024).toFixed(1)} MB`}
            />
            <VaultMetric
              label={t("metricRetention")}
              value={t("retentionValue")}
            />
          </div>

          <Card className="mb-6 p-4">
            <Dropzone />
          </Card>

          <Card className="overflow-hidden">
            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border bg-bg-panel-soft px-4 py-3">
              <div className="flex flex-wrap items-center gap-1 rounded-md border border-border bg-bg-canvas p-1">
                {STATUS_FILTERS.map((s) => (
                  <button
                    key={s.value}
                    type="button"
                    onClick={() => onStatusChange(s.value)}
                    className={cn(
                      "rounded px-2.5 py-1 text-[11px] font-medium transition-colors ring-focus",
                      statusFilter === s.value
                        ? "bg-bg-panel-elev text-text-primary"
                        : "text-text-muted hover:text-text-primary",
                    )}
                  >
                    {t(`filters.${s.i18nKey}`)}
                  </button>
                ))}
              </div>
              <span className="text-xs text-text-muted">
                {total === 0
                  ? t("zeroDocs")
                  : t("rangeOf", {
                      start: page * PAGE_SIZE + 1,
                      end: Math.min((page + 1) * PAGE_SIZE, total),
                      total,
                    })}
              </span>
            </div>

            {docs.isLoading && (
              <div className="space-y-2 p-4">
                {Array.from({ length: 5 }).map((_, i) => (
                  <Skeleton key={i} className="h-14" />
                ))}
              </div>
            )}

            {docs.isError && (
              <div className="p-6 text-xs text-status-danger">
                {t("loadFailed")} {(docs.error as Error)?.message}
              </div>
            )}

            <div className="divide-y divide-border">
              {rows.map((d) => {
                const tone = statusTone(d.status);
                const isBusy =
                  busyId === d.id ||
                  (analyzeMut.isPending && analyzeMut.variables === d.id);
                return (
                  <div
                    key={d.id}
                    className="grid grid-cols-1 gap-4 px-4 py-3.5 transition-colors hover:bg-bg-panel-elev md:grid-cols-[1fr_120px_120px_140px_220px]"
                  >
                    <button
                      type="button"
                      onClick={() => open(d)}
                      className="flex min-w-0 items-center gap-3 text-left ring-focus rounded-md"
                    >
                      <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md border border-border bg-bg-canvas">
                        <FileText className="w-4 h-4 text-status-info" />
                      </span>
                      <div className="min-w-0">
                        <div className="truncate text-sm font-medium">
                          {d.filename}
                        </div>
                        <div className="mt-0.5 truncate font-mono text-[11px] text-text-muted">
                          {d.mime_type} · {(d.size_bytes / 1024).toFixed(1)} KB
                          · {d.id}
                        </div>
                      </div>
                    </button>

                    <div className="hidden items-center text-xs text-text-muted md:flex">
                      {d.pages !== undefined && d.pages !== null
                        ? t("pages", { count: d.pages })
                        : "—"}
                    </div>

                    <div className="hidden items-center gap-1 text-xs text-text-muted md:flex">
                      <Clock size={12} /> {relativeTime(d.uploaded_at)}
                    </div>

                    <div className="flex items-center gap-2">
                      <span
                        className={cn(
                          "inline-flex items-center gap-1.5 rounded-md border px-2 py-1 text-[11px] font-medium",
                          tone.fg,
                          tone.bd,
                          tone.bg,
                        )}
                      >
                        <ShieldCheck size={12} />
                        {d.status}
                      </span>
                      {d.latest_report && (
                        <button
                          type="button"
                          onClick={() => viewReport(d)}
                          className={cn(
                            "rounded-md border border-border bg-bg-panel px-2 py-1 text-[11px] font-mono tabular-nums hover:bg-bg-panel-elev ring-focus",
                            scoreTone(d.latest_report.score),
                          )}
                          title={t("openReport", {
                            id: d.latest_report.report_id,
                          })}
                        >
                          {d.latest_report.score}
                        </button>
                      )}
                    </div>

                    <div className="flex items-center justify-end gap-1">
                      <Button
                        size="icon-sm"
                        variant="ghost"
                        title={t("runAnalysis")}
                        disabled={isBusy}
                        onClick={() => runAnalyze(d)}
                      >
                        {isBusy ? (
                          <Loader2 size={14} className="animate-spin" />
                        ) : (
                          <Play size={14} />
                        )}
                      </Button>
                      <Button
                        size="icon-sm"
                        variant="ghost"
                        title={t("downloadOriginal")}
                        disabled={isBusy}
                        onClick={() => runDownload(d)}
                      >
                        <Download size={14} />
                      </Button>
                      <Button
                        size="icon-sm"
                        variant="ghost"
                        title={t("openWorkspace")}
                        onClick={() => open(d)}
                      >
                        <FileText size={14} />
                      </Button>
                      <Button
                        size="icon-sm"
                        variant="ghost"
                        title={t("deleteDoc")}
                        disabled={isBusy}
                        onClick={() => setConfirmDel(d)}
                        className="text-status-danger hover:text-status-danger"
                      >
                        <Trash2 size={14} />
                      </Button>
                    </div>
                  </div>
                );
              })}
            </div>

            {!docs.isLoading && rows.length === 0 && (
              <div className="p-6">
                <EmptyState
                  icon={FileText}
                  title={
                    query || statusFilter !== "all"
                      ? t("noMatchTitle")
                      : t("vaultEmptyTitle")
                  }
                  description={
                    query || statusFilter !== "all"
                      ? t("noMatchDesc")
                      : t("vaultEmptyDesc")
                  }
                />
              </div>
            )}

            {totalPages > 1 && (
              <div className="flex items-center justify-between border-t border-border px-4 py-2.5">
                <span className="text-[11px] font-mono text-text-muted">
                  {t("page", { page: page + 1, total: totalPages })}
                </span>
                <div className="flex items-center gap-1">
                  <Button
                    size="icon-sm"
                    variant="ghost"
                    disabled={page === 0}
                    onClick={() => setPage((p) => Math.max(0, p - 1))}
                  >
                    <ChevronLeft size={14} />
                  </Button>
                  <Button
                    size="icon-sm"
                    variant="ghost"
                    disabled={page >= totalPages - 1}
                    onClick={() =>
                      setPage((p) => Math.min(totalPages - 1, p + 1))
                    }
                  >
                    <ChevronRight size={14} />
                  </Button>
                </div>
              </div>
            )}
          </Card>
        </div>
      </main>

      <ConfirmDialog
        open={confirmDel !== null}
        onOpenChange={(v) => !v && setConfirmDel(null)}
        title={t("deleteTitle")}
        description={
          confirmDel
            ? t("deleteDescription", { name: confirmDel.filename })
            : undefined
        }
        confirmLabel={t("deleteConfirm")}
        destructive
        busy={deleteMut.isPending}
        onConfirm={async () => {
          if (!confirmDel) return;
          try {
            await deleteMut.mutateAsync(confirmDel.id);
            setConfirmDel(null);
          } catch {
            // toast handled in mutation
          }
        }}
      />
    </div>
  );
}

function VaultMetric({ label, value }: { label: string; value: string }) {
  return (
    <Card className="p-4">
      <div className="text-[10px] uppercase tracking-wide text-text-muted">
        {label}
      </div>
      <div className="mt-2 text-xl font-semibold tabular-nums tracking-tight">
        {value}
      </div>
    </Card>
  );
}
