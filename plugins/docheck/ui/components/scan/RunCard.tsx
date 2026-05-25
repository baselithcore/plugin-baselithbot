"use client";

import { AlertTriangle, Loader2, Play, RefreshCw, Zap } from "lucide-react";
import { useTranslations } from "next-intl";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { StepHeader } from "./StepHeader";

interface Props {
  canRun: boolean;
  phase: string;
  error: string | null;
  onRun: () => void;
  onReset: () => void;
}

export function RunCard({ canRun, phase, error, onRun, onReset }: Props) {
  const t = useTranslations("scan.run");
  const busy = phase === "uploading" || phase === "analyzing";
  return (
    <Card>
      <CardContent className="pt-5">
        <StepHeader idx={4} icon={Zap} title={t("title")} hint={t("hint")} />
        <div className="flex items-center gap-2">
          <Button
            variant="primary"
            size="lg"
            disabled={!canRun}
            onClick={onRun}
            className="flex-1"
          >
            {busy ? (
              <>
                <Loader2 size={15} className="animate-spin" />{" "}
                {phase === "uploading" ? t("uploading") : t("analyzing")}
              </>
            ) : (
              <>
                <Play size={15} /> {t("runScan")}
              </>
            )}
          </Button>
          <Button
            variant="outline"
            size="lg"
            onClick={onReset}
            disabled={busy}
            title={t("reset")}
          >
            <RefreshCw size={14} />
          </Button>
        </div>
        {error && (
          <div className="mt-3 flex items-start gap-2 rounded-md border border-status-danger/30 bg-status-danger/10 p-2.5 text-[11px] text-status-danger">
            <AlertTriangle size={13} className="shrink-0 mt-0.5" />
            <span>{error}</span>
          </div>
        )}
        {phase === "analyzing" && (
          <div className="mt-3 text-[10px] uppercase tracking-wider text-text-muted flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-status-info animate-pulse" />
            {t("agentsRunning")}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
