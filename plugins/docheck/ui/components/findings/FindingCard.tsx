"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import {
  Ban,
  Check,
  ChevronDown,
  ClipboardCheck,
  Eye,
  FileSearch,
  Loader2,
  MessageSquareText,
  Quote,
  Search,
  X as XIcon,
  type LucideIcon,
} from "lucide-react";
import { SeverityBadge } from "@/components/ui/badge";
import { cn } from "@/lib/cn";
import { useAppStore } from "@/lib/store";
import { setFindingDecision, type DecisionKind, type Finding } from "@/lib/api";

const ACCENT: Record<Finding["severity"], string> = {
  FAIL: "before:bg-status-danger",
  WARN: "before:bg-status-warning",
  PASS: "before:bg-status-success",
  INFO: "before:bg-status-info",
};

interface Props {
  finding: Finding;
  selected?: boolean;
  onSelect?: (f: Finding) => void;
  onViewInDoc?: (f: Finding) => void;
}

export function FindingCard({
  finding,
  selected,
  onSelect,
  onViewInDoc,
}: Props) {
  const t = useTranslations("findings.card");
  const [openPolicy, setOpenPolicy] = useState(false);
  const [busy, setBusy] = useState<DecisionKind | null>(null);
  const [error, setError] = useState<string | null>(null);
  const openReasoning = useAppStore((s) => s.openReasoningFor);
  const decision = useAppStore((s) => s.decisions[finding.id]);
  const setDecision = useAppStore((s) => s.setDecision);
  const setAskFor = useAppStore((s) => s.setAskFor);
  const report = useAppStore((s) => s.currentReport);

  async function applyDecision(kind: DecisionKind) {
    if (!report?.report_id) {
      setError(t("errorReportUnavailable"));
      return;
    }
    setBusy(kind);
    setError(null);
    try {
      await setFindingDecision(report.report_id, finding.id, kind);
      setDecision(finding.id, kind);
    } catch (err) {
      setError(err instanceof Error ? err.message : t("errorFailed"));
    } finally {
      setBusy(null);
    }
  }

  return (
    <article
      role="listitem"
      data-expanded={openPolicy}
      onClick={() => {
        console.log("Card clicked!", finding.id, !!onSelect);
        onSelect?.(finding);
      }}
      className={cn(
        "group relative mb-3 cursor-pointer overflow-hidden rounded-lg border surface-elev p-3.5 transition-colors duration-150 ease-smooth",
        "before:absolute before:left-0 before:top-3 before:bottom-3 before:w-[3px] before:rounded-r-full",
        ACCENT[finding.severity],
        selected
          ? "border-status-info/50 ring-1 ring-status-info/30"
          : "border-border hover:border-border-strong hover:bg-bg-panel-elev",
      )}
    >
      <div className="flex items-start justify-between gap-3 pl-2">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <SeverityBadge severity={finding.severity} />
            <span className="font-mono text-[11px] text-text-secondary">
              {finding.rule_id}
            </span>
            <ConfidencePill value={finding.confidence} />
          </div>
          <h3 className="mt-2 text-[13px] font-semibold leading-snug text-text-primary">
            {finding.explanation}
          </h3>
        </div>
        <div className="shrink-0 rounded-md border border-border bg-bg-canvas px-2 py-1 text-right">
          <div className="text-[9px] uppercase tracking-wide text-text-muted">
            {t("lines")}
          </div>
          <div className="font-mono text-[11px] text-text-secondary">
            {finding.evidence.line_start}-{finding.evidence.line_end}
          </div>
        </div>
      </div>

      <div className="mt-3 grid grid-cols-2 gap-2 pl-2">
        <Meta
          label={t("policy")}
          value={`${finding.policy_ref.policy_id}@${finding.policy_ref.version}`}
        />
        <Meta
          label={t("page")}
          value={t("pageValue", {
            page: finding.evidence.page,
            chunk: finding.evidence.chunk_id.slice(0, 6),
          })}
        />
      </div>

      <button
        type="button"
        onClick={(e) => {
          e.stopPropagation();
          setOpenPolicy((v) => !v);
        }}
        aria-expanded={openPolicy}
        className="mt-3 ml-2 flex w-[calc(100%-0.5rem)] items-center justify-between rounded-md border border-border bg-bg-canvas px-3 py-2 text-xs text-text-secondary hover:bg-bg-panel hover:text-text-primary transition-colors ring-focus"
      >
        <span className="inline-flex items-center gap-2">
          <Quote size={13} className="text-text-muted" />
          {t("policyReference")}
        </span>
        <ChevronDown
          size={14}
          className={cn(
            "text-text-muted transition-transform duration-200",
            openPolicy && "rotate-180",
          )}
        />
      </button>
      {openPolicy && (
        <div className="mt-2 ml-2 rounded-md border border-border bg-bg-canvas p-3 animate-slide-up">
          <div className="mb-2 flex items-center gap-2 text-[10px] uppercase tracking-wide text-text-muted">
            <FileSearch size={12} />
            {t("verbatimExcerpt")}
          </div>
          <pre className="whitespace-pre-wrap font-mono text-[11px] leading-5 text-text-secondary">
            &quot;{finding.policy_ref.excerpt}&quot;
          </pre>
        </div>
      )}

      {finding.suggestion && (
        <div className="mt-3 ml-2 rounded-md border border-status-info/25 bg-status-info/8 p-3 text-[12px] leading-5 text-text-secondary">
          <ClipboardCheck className="mr-1.5 inline h-3.5 w-3.5 text-status-info" />
          {finding.suggestion}
        </div>
      )}

      <div className="mt-3 ml-2 flex flex-wrap gap-1.5">
        <ActionButton
          onClick={(e) => {
            e.stopPropagation();
            onViewInDoc?.(finding);
          }}
          icon={Eye}
        >
          {t("view")}
        </ActionButton>
        <ActionButton
          onClick={(e) => {
            e.stopPropagation();
            openReasoning(finding);
          }}
          icon={Search}
        >
          {t("reasoning")}
        </ActionButton>
        <ActionButton
          onClick={(e) => {
            e.stopPropagation();
            setAskFor(finding);
          }}
          icon={MessageSquareText}
          disabled={!report?.report_id}
        >
          {t("ask")}
        </ActionButton>
        <DecisionGroup
          current={decision}
          busy={busy}
          disabled={!report?.report_id}
          onPick={(k) => applyDecision(k)}
        />
      </div>
      {error && (
        <div className="mt-2 ml-2 text-[10px] text-status-danger">{error}</div>
      )}
    </article>
  );
}

function DecisionGroup({
  current,
  busy,
  disabled,
  onPick,
}: {
  current?: DecisionKind;
  busy: DecisionKind | null;
  disabled: boolean;
  onPick: (k: DecisionKind) => void;
}) {
  const t = useTranslations("findings.card");
  return (
    <div className="inline-flex items-center gap-px rounded-md border border-border bg-bg-canvas overflow-hidden">
      <DecisionBtn
        label={t("accept")}
        icon={Check}
        active={current === "accepted"}
        loading={busy === "accepted"}
        disabled={disabled}
        onClick={() => onPick("accepted")}
        tone="success"
      />
      <DecisionBtn
        label={t("reject")}
        icon={XIcon}
        active={current === "rejected"}
        loading={busy === "rejected"}
        disabled={disabled}
        onClick={() => onPick("rejected")}
        tone="danger"
      />
      <DecisionBtn
        label={t("mute")}
        icon={Ban}
        active={current === "muted"}
        loading={busy === "muted"}
        disabled={disabled}
        onClick={() => onPick("muted")}
        tone="muted"
      />
    </div>
  );
}

function DecisionBtn({
  label,
  icon: Icon,
  active,
  loading,
  disabled,
  onClick,
  tone,
}: {
  label: string;
  icon: LucideIcon;
  active: boolean;
  loading: boolean;
  disabled: boolean;
  onClick: () => void;
  tone: "success" | "danger" | "muted";
}) {
  const toneActive = {
    success: "bg-status-success/15 text-status-success",
    danger: "bg-status-danger/15 text-status-danger",
    muted: "bg-bg-panel-elev text-text-secondary",
  }[tone];
  return (
    <button
      type="button"
      aria-label={label}
      aria-pressed={active}
      disabled={disabled || loading}
      onClick={(e) => {
        e.stopPropagation();
        onClick();
      }}
      className={cn(
        "inline-flex h-7 items-center gap-1 px-2 text-[11px] transition-colors ring-focus",
        active
          ? toneActive
          : "text-text-secondary hover:bg-bg-panel-elev hover:text-text-primary",
        disabled && "opacity-50 cursor-not-allowed",
      )}
    >
      {loading ? (
        <Loader2 size={12} className="animate-spin" />
      ) : (
        <Icon size={12} />
      )}
      {label}
    </button>
  );
}

function Meta({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-w-0 rounded-md border border-border bg-bg-canvas/70 px-2.5 py-1.5">
      <div className="text-[9px] uppercase tracking-wide text-text-muted">
        {label}
      </div>
      <div className="mt-0.5 truncate font-mono text-[11px] text-text-secondary">
        {value}
      </div>
    </div>
  );
}

function ConfidencePill({ value }: { value: number }) {
  const pct = Math.round(value * 100);
  const tone =
    pct >= 80
      ? "text-status-success"
      : pct >= 60
        ? "text-status-warning"
        : "text-status-danger";
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full border border-border bg-bg-canvas px-1.5 py-0.5 text-[10px] font-mono",
        tone,
      )}
    >
      <span
        className={cn(
          "h-1.5 w-1.5 rounded-full",
          pct >= 80
            ? "bg-status-success"
            : pct >= 60
              ? "bg-status-warning"
              : "bg-status-danger",
        )}
      />
      {pct}%
    </span>
  );
}

function ActionButton({
  children,
  icon: Icon,
  onClick,
  disabled,
}: {
  children: React.ReactNode;
  icon: LucideIcon;
  onClick?: React.MouseEventHandler<HTMLButtonElement>;
  disabled?: boolean;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className={cn(
        "inline-flex h-7 items-center gap-1.5 rounded-md border border-border bg-bg-canvas px-2 text-[11px] transition-colors ring-focus",
        disabled
          ? "text-text-muted/60 cursor-not-allowed"
          : "text-text-secondary hover:bg-bg-panel-elev hover:text-text-primary",
      )}
    >
      <Icon size={12} /> {children}
    </button>
  );
}
