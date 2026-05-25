"use client";

import { Copy, Download, X } from "lucide-react";
import { useEffect } from "react";
import { useTranslations } from "next-intl";
import { useAppStore } from "@/lib/store";
import { SeverityBadge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ReasoningTimeline } from "./ReasoningTimeline";

export function ReasoningDrawer() {
  const t = useTranslations("reasoning");
  const finding = useAppStore((s) => s.selectedFinding);
  const open = useAppStore((s) => s.reasoningOpen);
  const setOpen = useAppStore((s) => s.setReasoningOpen);

  useEffect(() => {
    if (!open) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") setOpen(false);
    }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open, setOpen]);

  if (!open || !finding) return null;

  return (
    <>
      <div
        onClick={() => setOpen(false)}
        className="fixed inset-0 bg-bg-canvas/40 backdrop-blur-[2px] z-30 animate-fade-in"
      />
      <aside
        role="dialog"
        aria-label={t("title")}
        className="fixed top-0 right-0 bottom-0 w-[min(520px,100vw)] surface-elev border-l border-border z-40 flex flex-col animate-slide-up shadow-popover"
      >
        <header className="px-5 py-4 flex items-start justify-between gap-3 border-b border-border">
          <div className="min-w-0">
            <div className="text-[10px] font-semibold uppercase tracking-[0.18em] text-text-muted">
              {t("title")}
            </div>
            <div className="mt-1 flex items-center gap-2">
              <SeverityBadge severity={finding.severity} />
              <span className="truncate text-sm font-mono text-text-secondary">
                {finding.rule_id}
              </span>
            </div>
            <p className="mt-1.5 text-xs text-text-muted line-clamp-2">
              {finding.explanation}
            </p>
          </div>
          <button
            type="button"
            onClick={() => setOpen(false)}
            aria-label={t("close")}
            className="p-1.5 rounded-md hover:bg-bg-panel-elev text-text-muted hover:text-text-primary transition-colors"
          >
            <X size={16} />
          </button>
        </header>

        <div className="flex-1 overflow-auto px-5 py-4">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-xs font-semibold text-text-secondary uppercase tracking-wide">
              {t("agentTimeline")}
            </h2>
            <span className="text-[10px] font-mono text-text-muted">
              {t("steps", { count: finding.reasoning.length })}
            </span>
          </div>
          <ReasoningTimeline steps={finding.reasoning} />
        </div>

        <footer className="p-3 border-t border-border flex gap-2">
          <Button
            variant="outline"
            size="sm"
            className="flex-1"
            onClick={() =>
              navigator.clipboard.writeText(
                JSON.stringify(finding.reasoning, null, 2),
              )
            }
          >
            <Copy size={13} /> {t("copyJson")}
          </Button>
          <Button
            variant="outline"
            size="sm"
            className="flex-1"
            onClick={() => {
              const blob = new Blob([JSON.stringify(finding, null, 2)], {
                type: "application/json",
              });
              const url = URL.createObjectURL(blob);
              const a = document.createElement("a");
              a.href = url;
              a.download = `${finding.rule_id}-trace.json`;
              document.body.appendChild(a);
              a.click();
              a.remove();
              URL.revokeObjectURL(url);
            }}
          >
            <Download size={13} /> {t("exportTrace")}
          </Button>
        </footer>
      </aside>
    </>
  );
}
