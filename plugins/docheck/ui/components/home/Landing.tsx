"use client";

import { useQuery } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import {
  AlertTriangle,
  CheckCircle2,
  FileSearch,
  GaugeCircle,
  LockKeyhole,
  Network,
  Scale,
  ShieldCheck,
  type LucideIcon,
} from "lucide-react";

import { Dropzone } from "@/components/Dropzone";
import { PolicyToggleBoard } from "@/components/policy/PolicyToggleBoard";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { StatusDot } from "@/components/ui/status-dot";
import { getCacheMetrics, getHealth, getWorkspaceQueue } from "@/lib/api";
import { cn } from "@/lib/cn";

import { LandingExtras } from "./LandingExtras";

export function Landing() {
  return (
    <main className="flex-1 overflow-auto bg-bg-canvas">
      <div className="mx-auto max-w-7xl px-6 lg:px-8 py-8">
        <Hero />
        <PillarRow />
        <LandingExtras />
      </div>
    </main>
  );
}

function Hero() {
  const t = useTranslations("home");
  const health = useQuery({
    queryKey: ["health"],
    queryFn: getHealth,
    staleTime: 15_000,
    refetchInterval: 30_000,
  });
  const engineReady =
    !health.isError && !!health.data && health.data.status === "ok";
  return (
    <section className="grid gap-6 lg:grid-cols-[minmax(0,0.92fr)_minmax(420px,1.08fr)]">
      <div className="flex flex-col justify-between rounded-lg border border-border bg-bg-panel p-6 shadow-panel">
        <div>
          <div className="inline-flex items-center gap-2 rounded-md border border-border bg-bg-panel-elev px-2.5 py-1.5 text-xs font-medium text-text-secondary">
            <ShieldCheck
              size={13}
              className={
                engineReady ? "text-status-success" : "text-status-warning"
              }
            />
            {engineReady
              ? t("engineReady", { version: health.data?.version ?? "" })
              : health.isLoading
                ? t("engineCheck")
                : t("engineOffline")}
          </div>

          <h1 className="mt-7 max-w-2xl text-3xl font-semibold tracking-tight text-text-primary lg:text-4xl">
            {t("title")}
          </h1>

          <p className="mt-4 max-w-2xl text-sm leading-6 text-text-muted">
            {t("subtitle")}
          </p>
        </div>

        <div className="mt-8 flex flex-wrap items-center gap-3">
          <Button variant="primary" size="lg" asChild>
            <a href="#upload">
              <FileSearch size={16} />
              {t("newReview")}
            </a>
          </Button>
          <Button variant="outline" size="lg" asChild>
            <a href="/policies">
              <Scale size={16} />
              {t("policyRegistry")}
            </a>
          </Button>
        </div>

        <SignalsRow />
      </div>

      <div>
        <Card id="upload" className="overflow-hidden">
          <CardContent className="pt-5 pb-5">
            <div className="mb-6 flex items-center justify-between">
              <div className="text-left">
                <div className="text-[10px] uppercase tracking-[0.18em] text-text-muted font-semibold mb-1">
                  {t("intake")}
                </div>
                <h2 className="text-base font-semibold text-text-primary">
                  {t("uploadHeading")}
                </h2>
              </div>
              <div
                className={cn(
                  "hidden sm:flex items-center gap-2 text-xs font-medium px-2.5 py-1.5 rounded-md border",
                  engineReady
                    ? "text-status-success bg-status-success/10 border-status-success/20"
                    : "text-status-warning bg-status-warning/10 border-status-warning/20",
                )}
              >
                <StatusDot
                  tone={engineReady ? "success" : "warning"}
                  pulse={engineReady}
                />
                {engineReady
                  ? t("engineReady", { version: health.data?.version ?? "" })
                  : health.isLoading
                    ? t("engineProbing")
                    : t("engineOffline")}
              </div>
            </div>
            <div className="rounded-lg border border-border bg-bg-canvas">
              <div className="border-b border-border/50 p-3">
                <PolicyToggleBoard compact />
              </div>
              <Dropzone />
            </div>
          </CardContent>
        </Card>
      </div>
    </section>
  );
}

function SignalsRow() {
  const t = useTranslations("home.signals");
  const cache = useQuery({
    queryKey: ["cache-metrics"],
    queryFn: getCacheMetrics,
    staleTime: 30_000,
    refetchInterval: 60_000,
  });
  const queue = useQuery({
    queryKey: ["workspace-queue"],
    queryFn: getWorkspaceQueue,
    staleTime: 30_000,
    refetchInterval: 60_000,
  });
  const verdictRatio = cache.data?.verdict?.ratio;
  const ratioPct =
    typeof verdictRatio === "number"
      ? `${Math.round(verdictRatio * 100)}%`
      : "—";
  const total = queue.data
    ? queue.data.in_review.value +
      queue.data.pending_approval.value +
      queue.data.compliant.value
    : null;
  return (
    <div className="mt-8 grid grid-cols-1 gap-3 sm:grid-cols-3">
      <Signal icon={Network} label={t("fanout")} value={t("fanoutValue")} />
      <Signal
        icon={LockKeyhole}
        label={t("cache")}
        value={cache.isLoading ? "…" : ratioPct}
      />
      <Signal
        icon={GaugeCircle}
        label={t("tracked")}
        value={queue.isLoading ? "…" : total !== null ? String(total) : "—"}
      />
    </div>
  );
}

function Signal({
  icon: Icon,
  label,
  value,
}: {
  icon: LucideIcon;
  label: string;
  value: string;
}) {
  return (
    <div className="rounded-lg border border-border bg-bg-canvas/70 p-3 transition-colors hover:border-border-strong">
      <Icon size={15} className="text-status-info" />
      <div className="mt-3 text-[10px] uppercase tracking-wide text-text-muted">
        {label}
      </div>
      <div className="mt-0.5 text-sm font-semibold text-text-primary">
        {value}
      </div>
    </div>
  );
}

function PillarRow() {
  const t = useTranslations("home.pillars");
  const items = [
    {
      step: "01",
      title: t("extract.title"),
      text: t("extract.text"),
      icon: FileSearch,
      tone: "info" as const,
    },
    {
      step: "02",
      title: t("rank.title"),
      text: t("rank.text"),
      icon: AlertTriangle,
      tone: "warning" as const,
    },
    {
      step: "03",
      title: t("seal.title"),
      text: t("seal.text"),
      icon: CheckCircle2,
      tone: "success" as const,
    },
  ];
  return (
    <section className="mt-8 grid gap-4 lg:grid-cols-3">
      {items.map((it) => (
        <PillarCard key={it.step} {...it} />
      ))}
    </section>
  );
}

function PillarCard({
  step,
  title,
  text,
  icon: Icon,
  tone,
}: {
  step: string;
  title: string;
  text: string;
  icon: LucideIcon;
  tone: "info" | "warning" | "success";
}) {
  const TONE = {
    info: "text-status-info bg-status-info/10 border-status-info/30 shadow-[0_0_15px_rgba(14,165,233,0.15)]",
    warning:
      "text-status-warning bg-status-warning/10 border-status-warning/30 shadow-[0_0_15px_rgba(245,158,11,0.15)]",
    success:
      "text-status-success bg-status-success/10 border-status-success/30 shadow-[0_0_15px_rgba(16,185,129,0.15)]",
  }[tone];
  return (
    <Card interactive className="relative overflow-hidden p-5 group">
      <div className="relative z-10 flex items-center justify-between">
        <span className="font-mono text-xs uppercase tracking-widest text-text-muted">
          {step}
        </span>
        <span
          className={`flex h-9 w-9 items-center justify-center rounded-md border ${TONE}`}
        >
          <Icon size={20} />
        </span>
      </div>
      <h3 className="relative z-10 mt-6 text-lg font-semibold tracking-tight text-text-primary">
        {title}
      </h3>
      <p className="relative z-10 mt-3 text-sm leading-relaxed text-text-secondary">
        {text}
      </p>
    </Card>
  );
}
