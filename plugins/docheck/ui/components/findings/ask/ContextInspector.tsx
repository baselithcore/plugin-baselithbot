"use client";

import {
  ChevronDown,
  FileSearch,
  Quote,
  ScrollText,
  ShieldCheck,
} from "lucide-react";
import type { Finding } from "@/lib/api";
import { cn } from "@/lib/cn";
import type { T } from "./atoms";

interface Props {
  finding: Finding;
  open: boolean;
  onToggle: () => void;
  t: T;
}

export function ContextInspector({ finding, open, onToggle, t }: Props) {
  return (
    <div className="border-b border-border bg-bg-panel-soft/40">
      <button
        type="button"
        onClick={onToggle}
        aria-expanded={open}
        className="w-full px-5 py-2.5 flex items-center justify-between text-[11px] font-medium text-text-secondary hover:text-text-primary transition-colors ring-focus"
      >
        <span className="inline-flex items-center gap-2">
          <ShieldCheck size={12} className="text-status-success" />
          {t("contextLabel")}
          <span className="text-[10px] text-text-muted font-mono">
            ({t("contextHint")})
          </span>
        </span>
        <ChevronDown
          size={14}
          className={cn(
            "text-text-muted transition-transform duration-200",
            open && "rotate-180",
          )}
        />
      </button>
      {open && (
        <div className="px-5 pb-3 space-y-2.5 animate-slide-up">
          <Block
            icon={Quote}
            label={t("contextPolicy")}
            meta={`${finding.policy_ref.policy_id} · ${finding.policy_ref.title}`}
            body={finding.policy_ref.excerpt}
          />
          {finding.evidence.text && (
            <Block
              icon={FileSearch}
              label={t("contextEvidence")}
              meta={t("contextEvidenceMeta", {
                page: finding.evidence.page,
                start: finding.evidence.line_start,
                end: finding.evidence.line_end,
              })}
              body={finding.evidence.snippet || finding.evidence.text}
            />
          )}
          {finding.reasoning?.length > 0 && (
            <Block
              icon={ScrollText}
              label={t("contextReasoning")}
              meta={t("contextReasoningMeta", {
                count: finding.reasoning.length,
              })}
              body={
                finding.reasoning
                  .slice(0, 3)
                  .map(
                    (s) => `• ${s.agent}${s.thought ? ` — ${s.thought}` : ""}`,
                  )
                  .join("\n") + (finding.reasoning.length > 3 ? "\n…" : "")
              }
            />
          )}
        </div>
      )}
    </div>
  );
}

function Block({
  icon: Icon,
  label,
  meta,
  body,
}: {
  icon: typeof Quote;
  label: string;
  meta: string;
  body: string;
}) {
  return (
    <div className="rounded-md border border-border bg-bg-canvas px-3 py-2">
      <div className="flex items-center justify-between text-[10px] uppercase tracking-wide text-text-muted">
        <span className="inline-flex items-center gap-1.5">
          <Icon size={11} />
          {label}
        </span>
        <span className="font-mono normal-case truncate ml-2 max-w-[60%]">
          {meta}
        </span>
      </div>
      <pre className="mt-1.5 whitespace-pre-wrap font-mono text-[11px] leading-5 text-text-secondary line-clamp-4">
        {body}
      </pre>
    </div>
  );
}
