"use client";

import {
  Brain,
  ChevronRight,
  Loader2,
  RefreshCw,
  ShieldAlert,
  Sparkles,
  type LucideIcon,
} from "lucide-react";
import { useTranslations } from "next-intl";
import type { Report, ReportSummary, Severity } from "@/lib/api";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { SeverityBadge } from "@/components/ui/badge";
import { ScoreGauge } from "@/components/ui/ScoreGauge";
import { cn } from "@/lib/cn";

interface Props {
  report: Report | null;
  phase: string;
  summary: ReportSummary | null;
  summaryLoading: boolean;
  summaryError: string | null;
  onRetrySummary: () => void;
}

export function VerdictCard({
  report,
  phase,
  summary,
  summaryLoading,
  summaryError,
  onRetrySummary,
}: Props) {
  const t = useTranslations("scan.verdict");
  if (!report && phase !== "analyzing" && phase !== "uploading") {
    return (
      <Card>
        <CardContent className="pt-5">
          <div className="flex flex-col items-center justify-center text-center py-8">
            <div className="flex h-11 w-11 items-center justify-center rounded-md border border-border bg-bg-panel-elev text-text-muted">
              <Sparkles size={18} />
            </div>
            <div className="mt-3 text-sm font-semibold">{t("noScanTitle")}</div>
            <p className="mt-1 text-xs text-text-muted max-w-sm">
              {t("noScanText")}
            </p>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (phase === "uploading" || phase === "analyzing") {
    return (
      <Card>
        <CardContent className="pt-5">
          <div className="flex items-center gap-3">
            <Loader2 size={18} className="animate-spin text-status-info" />
            <div>
              <div className="text-sm font-semibold">
                {phase === "uploading" ? t("uploading") : t("running")}
              </div>
              <div className="text-[11px] text-text-muted">
                {t("willAppear")}
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (!report) return null;

  const verdict = summary?.verdict;
  const tone =
    verdict === "compliant"
      ? "success"
      : verdict === "critical"
        ? "danger"
        : "warning";
  const verdictCls = {
    success:
      "border-status-success/30 bg-status-success/10 text-status-success",
    warning:
      "border-status-warning/30 bg-status-warning/10 text-status-warning",
    danger: "border-status-danger/30 bg-status-danger/10 text-status-danger",
  }[tone];

  return (
    <Card>
      <CardContent className="pt-5">
        <div className="flex items-start gap-5">
          <ScoreGauge score={report.score} size={88} />
          <div className="min-w-0 flex-1">
            <div className="flex items-center justify-between gap-3">
              <div className="text-[10px] uppercase tracking-[0.2em] text-text-muted">
                {t("scanVerdict")}
              </div>
              <Button
                size="sm"
                variant="ghost"
                onClick={onRetrySummary}
                disabled={summaryLoading}
              >
                <RefreshCw
                  size={11}
                  className={summaryLoading ? "animate-spin" : ""}
                />
                {summaryLoading ? t("generating") : t("regenerate")}
              </Button>
            </div>
            <div className="mt-1 flex items-center gap-2 flex-wrap">
              {summary && (
                <span
                  className={cn(
                    "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-[11px] font-medium uppercase tracking-wider",
                    verdictCls,
                  )}
                >
                  <Brain size={11} />
                  {summary.verdict}
                </span>
              )}
              {Object.entries(report.by_severity).map(([k, v]) =>
                Number(v) > 0 ? (
                  <span
                    key={k}
                    className="inline-flex items-center gap-1 text-[11px] text-text-secondary font-mono"
                  >
                    <SeverityBadge
                      severity={k as Severity}
                      className="!px-1.5 !h-[18px] !text-[10px]"
                    />
                    {String(v)}
                  </span>
                ) : null,
              )}
            </div>
            <h3 className="mt-3 text-base font-semibold tracking-tight">
              {summaryLoading
                ? t("judging")
                : summary?.headline ||
                  (summaryError
                    ? t("headlineUnavailable")
                    : t("headlineAwaiting"))}
            </h3>
            <p className="mt-2 text-sm leading-6 text-text-secondary">
              {summaryLoading ? (
                <span className="inline-flex items-center gap-1.5 text-text-muted text-xs">
                  <Loader2 size={11} className="animate-spin" />{" "}
                  {t("synthesizing", { count: report.findings.length })}
                </span>
              ) : summary?.assessment ? (
                summary.assessment
              ) : summaryError ? (
                <span className="text-status-warning text-xs">
                  {summaryError}
                </span>
              ) : null}
            </p>
          </div>
        </div>

        {summary &&
          (summary.top_risks.length > 0 || summary.next_steps.length > 0) && (
            <div className="mt-5 grid gap-3 md:grid-cols-2">
              {summary.top_risks.length > 0 && (
                <BulletBox
                  icon={ShieldAlert}
                  title={t("topRisks")}
                  tone="danger"
                  items={summary.top_risks}
                />
              )}
              {summary.next_steps.length > 0 && (
                <BulletBox
                  icon={ChevronRight}
                  title={t("nextSteps")}
                  tone="info"
                  items={summary.next_steps}
                />
              )}
            </div>
          )}
      </CardContent>
    </Card>
  );
}

function BulletBox({
  icon: Icon,
  title,
  tone,
  items,
}: {
  icon: LucideIcon;
  title: string;
  tone: "danger" | "info";
  items: string[];
}) {
  const cls =
    tone === "danger"
      ? "border-status-danger/25 bg-status-danger/5"
      : "border-status-info/25 bg-status-info/5";
  const iconCls = tone === "danger" ? "text-status-danger" : "text-status-info";
  const dotCls = tone === "danger" ? "bg-status-danger" : "bg-status-info";
  return (
    <div className={cn("rounded-lg border p-3", cls)}>
      <div className="flex items-center gap-1.5 text-[10px] uppercase tracking-wider text-text-secondary font-semibold">
        <Icon size={11} className={iconCls} />
        {title}
      </div>
      <ul className="mt-2 space-y-1.5">
        {items.map((it, i) => (
          <li
            key={i}
            className="flex items-start gap-2 text-xs text-text-secondary leading-5"
          >
            <span
              className={cn("mt-1.5 h-1 w-1 rounded-full shrink-0", dotCls)}
            />
            <span>{it}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
