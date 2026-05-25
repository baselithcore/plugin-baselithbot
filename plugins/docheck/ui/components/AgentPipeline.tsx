"use client";

import {
  AlertCircle,
  Brain,
  CheckCircle2,
  ClipboardCheck,
  FileSearch,
  Loader2,
  Scale,
  ShieldCheck,
  type LucideIcon,
} from "lucide-react";
import { useTranslations } from "next-intl";
import { cn } from "@/lib/cn";

const STAGE_DEFS = [
  { id: "structurer", icon: FileSearch },
  { id: "legal", icon: Scale },
  { id: "technical", icon: Brain },
  { id: "pii", icon: ShieldCheck },
  { id: "synthesizer", icon: ClipboardCheck },
] as const;

function useStages() {
  const t = useTranslations("agentPipeline.stages");
  return STAGE_DEFS.map((s) => {
    switch (s.id) {
      case "structurer":
        return { ...s, label: t("structurer"), desc: t("structurerDesc") };
      case "legal":
        return { ...s, label: t("legal"), desc: t("legalDesc") };
      case "technical":
        return { ...s, label: t("technical"), desc: t("technicalDesc") };
      case "pii":
        return { ...s, label: t("pii"), desc: t("piiDesc") };
      case "synthesizer":
        return { ...s, label: t("synthesis"), desc: t("synthesisDesc") };
    }
  });
}

const STAGES = STAGE_DEFS;

type StageId = (typeof STAGES)[number]["id"];
type Status = "pending" | "active" | "done";

interface Props {
  phase: string;
  progress: { current: number; total: number; label?: string } | null;
  done: boolean;
  error: string | null;
  variant?: "compact" | "full";
}

export function AgentPipeline({
  phase,
  progress,
  done,
  error,
  variant = "compact",
}: Props) {
  const t = useTranslations("agentPipeline");
  const stages = useStages();
  if (error) {
    return (
      <div className="flex items-center gap-2 rounded-md border border-status-danger/30 bg-status-danger/10 px-3 py-2 text-xs text-status-danger animate-fade-in">
        <AlertCircle size={14} /> {error}
      </div>
    );
  }

  const currentIdx = STAGES.findIndex((s) => s.id === phase);
  const overall = done
    ? 100
    : progress
      ? Math.round((progress.current / Math.max(1, progress.total)) * 100)
      : Math.max(0, Math.min(95, ((currentIdx + 1) / STAGES.length) * 100));

  function statusFor(idx: number): Status {
    if (done) return "done";
    if (currentIdx === -1) return idx === 0 ? "active" : "pending";
    if (idx < currentIdx) return "done";
    if (idx === currentIdx) return "active";
    return "pending";
  }

  if (variant === "full") {
    return (
      <div className="rounded-xl border border-border surface-elev p-4 shadow-panel animate-fade-in">
        <Header
          done={done}
          progress={progress}
          overall={overall}
          phase={phase}
        />
        <div className="mt-4 grid grid-cols-5 gap-2">
          {stages.map((stage, idx) => (
            <NodeCard key={stage.id} stage={stage} status={statusFor(idx)} />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-2 animate-fade-in">
      <div className="flex items-center gap-3 rounded-md border border-border bg-bg-panel-elev px-3 py-2">
        {done ? (
          <CheckCircle2 size={14} className="text-status-success" />
        ) : (
          <Loader2
            size={14}
            className="animate-spin text-status-info shrink-0"
          />
        )}
        <div
          className="flex flex-1 items-center gap-1"
          aria-label={t("ariaStages")}
        >
          {stages.map((stage, idx) => {
            const st = statusFor(idx);
            return (
              <span
                key={stage.id}
                className="group flex flex-1 items-center"
                title={stage.label}
              >
                <span
                  className={cn(
                    "h-1.5 flex-1 rounded-full transition-all duration-300",
                    st === "done" && "bg-status-success",
                    st === "active" &&
                      "bg-status-info shadow-[0_0_12px_rgba(47,123,255,0.6)]",
                    st === "pending" && "bg-border",
                  )}
                />
                {idx < STAGES.length - 1 && <span className="w-1" />}
              </span>
            );
          })}
        </div>
        <span className="font-mono text-[11px] tabular-nums text-text-secondary min-w-[3ch] text-right">
          {overall}%
        </span>
        <span className="hidden md:inline text-xs font-medium text-text-secondary capitalize min-w-[110px]">
          {done
            ? t("completed")
            : currentIdx >= 0
              ? stages[currentIdx].label
              : phase || t("starting")}
        </span>
        {progress && !done && (
          <span className="hidden lg:inline text-[11px] text-text-muted">
            {progress.current}/{progress.total} {progress.label ?? ""}
          </span>
        )}
      </div>
    </div>
  );
}

function Header({
  done,
  progress,
  overall,
  phase,
}: {
  done: boolean;
  progress: Props["progress"];
  overall: number;
  phase: string;
}) {
  const t = useTranslations("agentPipeline");
  return (
    <div className="flex items-center justify-between gap-4">
      <div className="min-w-0">
        <div className="flex items-center gap-2 text-[10px] font-semibold uppercase tracking-[0.18em] text-text-muted">
          <span
            className={cn(
              "inline-block h-1.5 w-1.5 rounded-full",
              done ? "bg-status-success" : "bg-status-info animate-pulse-soft",
            )}
          />
          {done ? t("complete") : t("running")}
        </div>
        <div className="mt-1 text-sm font-semibold capitalize">
          {done ? t("allFinished") : phase || t("starting")}
          {progress && !done && (
            <span className="ml-2 font-mono text-[11px] text-text-muted">
              · {progress.current}/{progress.total} {progress.label ?? ""}
            </span>
          )}
        </div>
      </div>
      <div className="text-right">
        <div className="font-mono text-[11px] uppercase tracking-wide text-text-muted">
          Overall
        </div>
        <div className="text-2xl font-semibold tabular-nums text-text-primary">
          {overall}%
        </div>
      </div>
    </div>
  );
}

function NodeCard({
  stage,
  status,
}: {
  stage: { id: StageId; label: string; desc: string; icon: LucideIcon };
  status: Status;
}) {
  const Icon = stage.icon;
  return (
    <div
      className={cn(
        "relative rounded-lg border p-3 transition-all duration-300",
        status === "done" && "border-status-success/30 bg-status-success/5",
        status === "active" && "border-status-info/40 bg-status-info/8",
        status === "pending" && "border-border bg-bg-canvas",
      )}
    >
      <div
        className={cn(
          "flex h-8 w-8 items-center justify-center rounded-md border",
          status === "done" &&
            "border-status-success/30 bg-status-success/10 text-status-success",
          status === "active" &&
            "border-status-info/40 bg-status-info/15 text-status-info",
          status === "pending" && "border-border bg-bg-panel text-text-muted",
        )}
      >
        {status === "active" ? (
          <Loader2 size={14} className="animate-spin" />
        ) : (
          <Icon size={14} />
        )}
      </div>
      <div className="mt-2.5 text-[11px] font-semibold text-text-primary">
        {stage.label}
      </div>
      <div className="mt-0.5 text-[10px] leading-4 text-text-muted">
        {stage.desc}
      </div>
      {status === "active" && (
        <div className="absolute inset-x-0 bottom-0 h-[2px] overflow-hidden rounded-b-lg">
          <div className="stripe-loading h-full" />
        </div>
      )}
    </div>
  );
}
