"use client";

import { useQuery } from "@tanstack/react-query";
import { ArrowUpRight, Brain } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  getActivePolicies,
  getRecentActivity,
  getWorkspaceQueue,
  type ActivePolicy,
  type RecentActivity,
} from "@/lib/api";
import { cn } from "@/lib/cn";
import { useAppStore } from "@/lib/store";

export function LandingExtras() {
  return (
    <>
      <RecentRow />
      <BottomRow />
    </>
  );
}

function RecentRow() {
  const t = useTranslations("landingExtras");
  const recent = useQuery({
    queryKey: ["recent-activity"],
    queryFn: () => getRecentActivity(5),
    staleTime: 15_000,
    refetchInterval: 45_000,
  });
  const setDocId = useAppStore((s) => s.setCurrentDocId);
  const setReport = useAppStore((s) => s.setCurrentReport);
  const router = useRouter();
  const items = recent.data ?? [];
  return (
    <section className="mt-8">
      <div className="mb-3 flex items-end justify-between">
        <div>
          <div className="text-[10px] uppercase tracking-[0.2em] text-text-muted">
            {t("recentEyebrow")}
          </div>
          <h2 className="mt-1 text-lg font-semibold tracking-tight">
            {t("recentTitle")}
          </h2>
        </div>
        <Button variant="ghost" size="sm" asChild>
          <Link href="/documents">
            {t("openVault")} <ArrowUpRight size={13} />
          </Link>
        </Button>
      </div>
      {recent.isLoading ? (
        <div className="grid gap-2 md:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-20" />
          ))}
        </div>
      ) : items.length === 0 ? (
        <Card className="p-6 text-center">
          <p className="text-sm text-text-muted">{t("noAnalyses")}</p>
        </Card>
      ) : (
        <div className="grid gap-2 md:grid-cols-2 lg:grid-cols-3">
          {items.map((r) => (
            <RecentCard
              key={r.report_id}
              item={r}
              onOpen={() => {
                setDocId(r.doc_id);
                setReport(null);
                router.push(`/?doc=${r.doc_id}&report=${r.report_id}`);
              }}
            />
          ))}
        </div>
      )}
    </section>
  );
}

function RecentCard({
  item,
  onOpen,
}: {
  item: RecentActivity;
  onOpen: () => void;
}) {
  const t = useTranslations("landingExtras");
  const tone =
    item.score >= 80 ? "success" : item.score >= 60 ? "warning" : "danger";
  const cls = {
    success:
      "border-status-success/30 text-status-success bg-status-success/10",
    warning:
      "border-status-warning/30 text-status-warning bg-status-warning/10",
    danger: "border-status-danger/30 text-status-danger bg-status-danger/10",
  }[tone];
  return (
    <button
      type="button"
      onClick={onOpen}
      className="group rounded-xl border border-border bg-bg-canvas p-4 text-left transition-colors hover:border-border-strong hover:bg-bg-panel-elev"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="truncate text-sm font-semibold text-text-primary">
            {item.filename}
          </div>
          <div className="mt-0.5 truncate font-mono text-[10px] text-text-muted">
            {item.doc_id}
          </div>
        </div>
        <span
          className={cn(
            "shrink-0 rounded-full border px-2 py-0.5 text-[10px] font-mono",
            cls,
          )}
        >
          {item.score}
        </span>
      </div>
      <div className="mt-3 flex items-center justify-between text-[11px] text-text-muted">
        <span>{new Date(item.signed_at).toLocaleString()}</span>
        <span className="inline-flex items-center gap-1 group-hover:text-status-info">
          {t("open")} <ArrowUpRight size={11} />
        </span>
      </div>
    </button>
  );
}

function BottomRow() {
  const t = useTranslations("landingExtras");
  const tQ = useTranslations("queue");
  const queue = useQuery({
    queryKey: ["workspace-queue"],
    queryFn: getWorkspaceQueue,
    staleTime: 15_000,
    refetchInterval: 30_000,
  });
  const policies = useQuery({
    queryKey: ["active-policies"],
    queryFn: getActivePolicies,
    staleTime: 60_000,
  });

  return (
    <section className="mt-8 grid gap-4 lg:grid-cols-[1fr_400px] mb-10">
      <Card className="p-5">
        <div className="flex items-center justify-between border-b border-border pb-4">
          <div>
            <h2 className="text-sm font-semibold">{t("operationalQueue")}</h2>
            <p className="mt-1 text-xs text-text-muted">{t("queueDesc")}</p>
          </div>
          <Button variant="ghost" size="sm" asChild>
            <Link href="/documents">
              {t("openVault")} <ArrowUpRight size={13} />
            </Link>
          </Button>
        </div>
        <div className="mt-4 grid gap-3 md:grid-cols-3">
          {queue.isLoading || !queue.data ? (
            Array.from({ length: 3 }).map((_, i) => (
              <Skeleton key={i} className="h-24" />
            ))
          ) : (
            <>
              <QueueMetric
                label={tQ("inReview")}
                tone="info"
                value={String(queue.data.in_review.value)}
                trend={trendStr(queue.data.in_review.trend_7d)}
                window="7d"
              />
              <QueueMetric
                label={tQ("pendingApproval")}
                tone="warning"
                value={String(queue.data.pending_approval.value)}
                trend={trendStr(queue.data.pending_approval.trend_7d)}
                window="7d"
              />
              <QueueMetric
                label={tQ("compliant")}
                tone="success"
                value={String(queue.data.compliant.value)}
                trend={trendStr(queue.data.compliant.trend_30d)}
                window="30d"
              />
            </>
          )}
        </div>
      </Card>

      <Card className="p-5">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold flex items-center gap-2">
            <Brain size={14} className="text-status-info" />
            {t("activePolicies")}
          </h2>
          <Button variant="ghost" size="sm" asChild>
            <Link href="/policies">
              {t("manage")} <ArrowUpRight size={13} />
            </Link>
          </Button>
        </div>
        <div className="mt-4 space-y-2">
          {policies.isLoading ? (
            Array.from({ length: 3 }).map((_, i) => (
              <Skeleton key={i} className="h-12" />
            ))
          ) : (policies.data ?? []).length === 0 ? (
            <p className="text-xs text-text-muted">{t("noActivePolicy")}</p>
          ) : (
            (policies.data ?? []).map((p) => (
              <ActivePolicyRow key={`${p.id}@${p.version}`} policy={p} />
            ))
          )}
        </div>
      </Card>
    </section>
  );
}

function ActivePolicyRow({ policy }: { policy: ActivePolicy }) {
  const t = useTranslations("landingExtras");
  const meta = `${policy.scope.replace("_", " ")} · v${policy.version} · ${policy.lang.toUpperCase()}`;
  return (
    <div className="flex items-center justify-between rounded-lg border border-border bg-bg-canvas px-3 py-2.5 hover:border-border-strong transition-colors">
      <div className="min-w-0">
        <div className="truncate text-xs font-mono text-text-secondary">
          {policy.id}
        </div>
        <div className="truncate text-[10px] text-text-muted mt-0.5">
          {meta}
        </div>
      </div>
      <span className="rounded-full border border-status-success/30 bg-status-success/10 px-2 py-0.5 text-[10px] font-medium text-status-success">
        {t("active")}
      </span>
    </div>
  );
}

function trendStr(n: number | undefined): string {
  if (n == null) return "0";
  if (n === 0) return "0";
  return n > 0 ? `+${n}` : String(n);
}

function QueueMetric({
  label,
  value,
  tone,
  trend,
  window = "7d",
}: {
  label: string;
  value: string;
  tone: "info" | "warning" | "success";
  trend: string;
  window?: string;
}) {
  const t = useTranslations("landingExtras");
  const TONE = {
    info: "text-status-info bg-status-info/10 border-status-info/30",
    warning:
      "text-status-warning bg-status-warning/10 border-status-warning/30",
    success:
      "text-status-success bg-status-success/10 border-status-success/30",
  }[tone];
  const trendUp = trend.startsWith("+");
  return (
    <div className="rounded-lg border border-border bg-bg-canvas p-4 transition-colors hover:border-border-strong">
      <div className="flex items-center justify-between">
        <span className="text-xs text-text-muted">{label}</span>
        <span
          className={`rounded-full border px-2 py-0.5 text-[10px] font-medium ${TONE}`}
        >
          {t("live")}
        </span>
      </div>
      <div className="mt-2 flex items-end justify-between">
        <span className="text-3xl font-semibold tabular-nums tracking-tight">
          {value}
        </span>
        <span
          className={`text-[11px] font-mono ${trendUp ? "text-status-success" : trend === "0" ? "text-text-muted" : "text-status-warning"}`}
        >
          {trend} {window}
        </span>
      </div>
    </div>
  );
}
