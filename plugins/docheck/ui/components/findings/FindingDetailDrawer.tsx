"use client";

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import {
  Ban,
  Check,
  ClipboardCheck,
  Copy,
  ExternalLink,
  FileSearch,
  Hash,
  Lightbulb,
  Loader2,
  MapPin,
  MessageSquareText,
  Quote,
  ScrollText,
  ShieldCheck,
  Sparkles,
  X,
  type LucideIcon,
} from "lucide-react";
import { useAppStore } from "@/lib/store";
import { setFindingDecision, type DecisionKind, type Finding } from "@/lib/api";
import { SeverityBadge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/cn";
import { EvidenceText } from "./EvidenceText";

const SEVERITY_TONE: Record<Finding["severity"], string> = {
  FAIL: "border-status-danger/40 bg-status-danger/10 text-status-danger",
  WARN: "border-status-warning/40 bg-status-warning/10 text-status-warning",
  PASS: "border-status-success/40 bg-status-success/10 text-status-success",
  INFO: "border-status-info/40 bg-status-info/10 text-status-info",
};

export function FindingDetailDrawer() {
  const t = useTranslations("findings.detail");
  const finding = useAppStore((s) => s.selectedFinding);
  const open = useAppStore((s) => s.detailOpen);
  const setOpen = useAppStore((s) => s.setDetailOpen);
  const openReasoning = useAppStore((s) => s.openReasoningFor);
  const setAskFor = useAppStore((s) => s.setAskFor);
  const decision = useAppStore((s) =>
    finding ? s.decisions[finding.id] : undefined,
  );
  const setDecision = useAppStore((s) => s.setDecision);
  const report = useAppStore((s) => s.currentReport);

  const [busy, setBusy] = useState<DecisionKind | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (!open) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") setOpen(false);
    }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open, setOpen]);

  useEffect(() => {
    setError(null);
  }, [finding?.id]);

  if (!open || !finding) return null;

  const tone = SEVERITY_TONE[finding.severity];
  const sev = (() => {
    switch (finding.severity) {
      case "FAIL":
        return { label: t("severity.failLabel"), hint: t("severity.failHint") };
      case "WARN":
        return { label: t("severity.warnLabel"), hint: t("severity.warnHint") };
      case "PASS":
        return { label: t("severity.passLabel"), hint: t("severity.passHint") };
      case "INFO":
        return { label: t("severity.infoLabel"), hint: t("severity.infoHint") };
    }
  })();
  const conf = Math.round(finding.confidence * 100);
  const reportId = report?.report_id;

  async function applyDecision(kind: DecisionKind) {
    if (!reportId || !finding) {
      setError(t("errorReportUnavailable"));
      return;
    }
    setBusy(kind);
    setError(null);
    try {
      await setFindingDecision(reportId, finding.id, kind);
      setDecision(finding.id, kind);
    } catch (err) {
      setError(err instanceof Error ? err.message : t("errorGeneric"));
    } finally {
      setBusy(null);
    }
  }

  async function copyAll() {
    if (!finding) return;
    const payload = {
      id: finding.id,
      severity: finding.severity,
      rule_id: finding.rule_id,
      explanation: finding.explanation,
      suggestion: finding.suggestion,
      policy_ref: finding.policy_ref,
      evidence: finding.evidence,
    };
    await navigator.clipboard.writeText(JSON.stringify(payload, null, 2));
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  }

  return (
    <>
      <div
        onClick={() => setOpen(false)}
        className="fixed inset-0 bg-bg-canvas/40 backdrop-blur-[2px] z-30 animate-fade-in"
      />
      <aside
        role="dialog"
        aria-label={t("title")}
        className="fixed top-0 right-0 bottom-0 w-[min(640px,100vw)] surface-elev border-l border-border z-40 flex flex-col animate-slide-up shadow-popover"
      >
        <header className="px-5 py-4 border-b border-border">
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <div className="text-[10px] font-semibold uppercase tracking-[0.18em] text-text-muted">
                {t("title")}
              </div>
              <div className="mt-1.5 flex flex-wrap items-center gap-2">
                <SeverityBadge severity={finding.severity} />
                <span className="font-mono text-[11px] text-text-secondary">
                  {finding.rule_id}
                </span>
                <ConfidencePill value={conf} />
              </div>
              <h2 className="mt-2 text-[14px] font-semibold leading-snug text-text-primary">
                {finding.explanation}
              </h2>
            </div>
            <button
              type="button"
              onClick={() => setOpen(false)}
              aria-label={t("close")}
              className="p-1.5 rounded-md hover:bg-bg-panel-elev text-text-muted hover:text-text-primary transition-colors"
            >
              <X size={16} />
            </button>
          </div>
          <div
            className={cn(
              "mt-3 flex items-start gap-2 rounded-md border px-3 py-2 text-[11px] leading-5",
              tone,
            )}
          >
            <ShieldCheck size={13} className="mt-0.5 shrink-0" />
            <div>
              <strong className="font-semibold">{sev.label}.</strong>{" "}
              <span className="text-text-secondary">{sev.hint}</span>
            </div>
          </div>
        </header>

        <div className="flex-1 overflow-auto px-5 py-5 space-y-5">
          <Section icon={Lightbulb} title={t("howToFix")} tone="info">
            {finding.suggestion ? (
              <div className="rounded-md border border-status-info/25 bg-status-info/8 p-3.5">
                <div className="flex items-start gap-2 text-[13px] leading-6 text-text-primary">
                  <ClipboardCheck
                    size={14}
                    className="mt-0.5 shrink-0 text-status-info"
                  />
                  <span className="whitespace-pre-wrap">
                    {finding.suggestion}
                  </span>
                </div>
                <FixChecklist suggestion={finding.suggestion} />
              </div>
            ) : (
              <div className="rounded-md border border-dashed border-border bg-bg-canvas/60 p-3.5 text-[12px] text-text-muted">
                {t("noAutoFix")}{" "}
                <button
                  type="button"
                  onClick={() => setAskFor(finding)}
                  className="underline decoration-dotted text-status-info hover:text-status-info/80"
                >
                  {t("askLink")}
                </button>{" "}
                {t("askFallback")}
              </div>
            )}
          </Section>

          <Section icon={Quote} title={t("policyReference")}>
            <div className="rounded-md border border-border bg-bg-canvas p-3">
              <div className="mb-2 flex items-center justify-between text-[10px] uppercase tracking-wide text-text-muted">
                <span className="inline-flex items-center gap-1.5">
                  <FileSearch size={11} />
                  {finding.policy_ref.policy_id}@{finding.policy_ref.version}
                </span>
                <span className="font-mono normal-case">
                  {finding.policy_ref.title}
                </span>
              </div>
              <pre className="whitespace-pre-wrap font-mono text-[11.5px] leading-5 text-text-secondary">
                &quot;{finding.policy_ref.excerpt}&quot;
              </pre>
            </div>
          </Section>

          <Section icon={MapPin} title={t("evidenceInDoc")}>
            <div className="rounded-md border border-border bg-bg-canvas p-3 space-y-2">
              <div className="grid grid-cols-3 gap-2">
                <Meta
                  label={t("metaPage")}
                  value={String(finding.evidence.page)}
                />
                <Meta
                  label={t("metaLines")}
                  value={`${finding.evidence.line_start}-${finding.evidence.line_end}`}
                />
                <Meta
                  label={t("metaChunk")}
                  value={finding.evidence.chunk_id.slice(0, 8)}
                />
              </div>
              {finding.evidence.text && (
                <EvidenceText
                  evidence={finding.evidence}
                  fallbackQuote={
                    finding.evidence.snippet || finding.policy_ref.excerpt
                  }
                />
              )}
            </div>
          </Section>

          {finding.reasoning?.length > 0 && (
            <Section icon={ScrollText} title={t("reasoningChain")}>
              <div className="rounded-md border border-border bg-bg-canvas p-3">
                <ol className="space-y-1.5">
                  {finding.reasoning.slice(0, 3).map((s) => (
                    <li
                      key={s.step}
                      className="flex items-start gap-2 text-[11.5px] leading-5 text-text-secondary"
                    >
                      <Hash
                        size={10}
                        className="mt-1 shrink-0 text-text-muted"
                      />
                      <div className="min-w-0">
                        <span className="font-mono text-[10px] text-text-muted">
                          {s.agent}
                          {s.action ? ` · ${s.action}` : ""}
                        </span>
                        {s.thought && (
                          <p className="mt-0.5 line-clamp-2">{s.thought}</p>
                        )}
                      </div>
                    </li>
                  ))}
                </ol>
                <button
                  type="button"
                  onClick={() => {
                    setOpen(false);
                    openReasoning(finding);
                  }}
                  className="mt-2.5 inline-flex items-center gap-1 text-[11px] text-status-info hover:text-status-info/80"
                >
                  <ExternalLink size={11} />{" "}
                  {t("openTimeline", { count: finding.reasoning.length })}
                </button>
              </div>
            </Section>
          )}
        </div>

        <footer className="px-4 py-3 border-t border-border space-y-2">
          {error && (
            <div className="rounded-md border border-status-danger/30 bg-status-danger/10 px-3 py-2 text-[11px] text-status-danger">
              {error}
            </div>
          )}
          <div className="flex flex-wrap items-center gap-2">
            <DecisionBtn
              label={t("accept")}
              icon={Check}
              tone="success"
              active={decision === "accepted"}
              loading={busy === "accepted"}
              disabled={!reportId}
              onClick={() => applyDecision("accepted")}
            />
            <DecisionBtn
              label={t("reject")}
              icon={X}
              tone="danger"
              active={decision === "rejected"}
              loading={busy === "rejected"}
              disabled={!reportId}
              onClick={() => applyDecision("rejected")}
            />
            <DecisionBtn
              label={t("mute")}
              icon={Ban}
              tone="muted"
              active={decision === "muted"}
              loading={busy === "muted"}
              disabled={!reportId}
              onClick={() => applyDecision("muted")}
            />
            <div className="ml-auto flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setAskFor(finding)}
                disabled={!reportId}
              >
                <MessageSquareText size={13} /> {t("ask")}
              </Button>
              <Button variant="outline" size="sm" onClick={copyAll}>
                <Copy size={13} /> {copied ? t("copied") : t("copy")}
              </Button>
            </div>
          </div>
        </footer>
      </aside>
    </>
  );
}

function Section({
  icon: Icon,
  title,
  tone,
  children,
}: {
  icon: LucideIcon;
  title: string;
  tone?: "info";
  children: React.ReactNode;
}) {
  return (
    <section>
      <h3
        className={cn(
          "mb-2 flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wide",
          tone === "info" ? "text-status-info" : "text-text-secondary",
        )}
      >
        <Icon size={12} />
        {title}
      </h3>
      {children}
    </section>
  );
}

function Meta({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded border border-border bg-bg-panel-soft px-2 py-1.5">
      <div className="text-[9px] uppercase tracking-wide text-text-muted">
        {label}
      </div>
      <div className="mt-0.5 font-mono text-[11px] text-text-secondary truncate">
        {value}
      </div>
    </div>
  );
}

function ConfidencePill({ value }: { value: number }) {
  const tone =
    value >= 80
      ? "text-status-success"
      : value >= 60
        ? "text-status-warning"
        : "text-status-danger";
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full border border-border bg-bg-canvas px-1.5 py-0.5 text-[10px] font-mono",
        tone,
      )}
    >
      <Sparkles size={9} /> {value}%
    </span>
  );
}

function FixChecklist({ suggestion }: { suggestion: string }) {
  const lines = suggestion
    .split(/\n+|(?<=\.)\s+(?=[A-ZÀ-Ý])/)
    .map((s) => s.trim())
    .filter((s) => s.length > 4 && s.length < 240);
  if (lines.length < 2) return null;
  return (
    <ul className="mt-3 space-y-1.5 border-t border-status-info/20 pt-3">
      {lines.map((l, i) => (
        <li
          key={i}
          className="flex items-start gap-2 text-[12px] leading-5 text-text-secondary"
        >
          <span className="mt-1 inline-block h-1.5 w-1.5 shrink-0 rounded-full bg-status-info" />
          <span>{l.replace(/\.$/, "")}</span>
        </li>
      ))}
    </ul>
  );
}

function DecisionBtn({
  label,
  icon: Icon,
  tone,
  active,
  loading,
  disabled,
  onClick,
}: {
  label: string;
  icon: LucideIcon;
  tone: "success" | "danger" | "muted";
  active: boolean;
  loading: boolean;
  disabled: boolean;
  onClick: () => void;
}) {
  const toneActive = {
    success:
      "border-status-success/40 bg-status-success/15 text-status-success",
    danger: "border-status-danger/40 bg-status-danger/15 text-status-danger",
    muted: "border-border bg-bg-panel-elev text-text-secondary",
  }[tone];
  return (
    <button
      type="button"
      aria-pressed={active}
      disabled={disabled || loading}
      onClick={onClick}
      className={cn(
        "inline-flex h-8 items-center gap-1.5 rounded-md border px-3 text-[11.5px] font-medium transition-colors ring-focus",
        active
          ? toneActive
          : "border-border bg-bg-canvas text-text-secondary hover:bg-bg-panel-elev hover:text-text-primary",
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
