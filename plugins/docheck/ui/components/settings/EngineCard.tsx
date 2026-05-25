"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { Cpu, Loader2, PlugZap } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";
import {
  getRuntimeInfo,
  probeLLM,
  type LLMProbeResult,
} from "@/lib/api/system";
import { Mono, Row, Section, StatusPill } from "./SettingsShared";

export function EngineCard() {
  const t = useTranslations("settings.engine");
  const runtime = useQuery({
    queryKey: ["system", "runtime"],
    queryFn: getRuntimeInfo,
  });
  const [probe, setProbe] = useState<LLMProbeResult | null>(null);

  const probeMut = useMutation({
    mutationFn: probeLLM,
    onSuccess: (r) => {
      setProbe(r);
      if (r.ok) {
        toast.success(t("toastReachable", { ms: r.latency_ms }));
      } else {
        toast.error(r.error || t("toastUnreachable"));
      }
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const r = runtime.data;

  return (
    <Section
      title={t("title")}
      icon={Cpu}
      actions={
        <Button
          size="sm"
          variant="secondary"
          onClick={() => probeMut.mutate()}
          disabled={probeMut.isPending}
        >
          {probeMut.isPending ? (
            <Loader2 size={13} className="animate-spin" />
          ) : (
            <PlugZap size={13} />
          )}
          {t("testConnection")}
        </Button>
      }
    >
      <Row label={t("endpoint")}>
        <Mono>{r?.llm_base_url ?? "…"}</Mono>
      </Row>
      <Row label={t("primaryModel")}>
        <Mono>{r?.llm_primary_model ?? "…"}</Mono>
      </Row>
      <Row label={t("fallbackModel")}>
        <Mono>{r?.llm_fallback_model ?? "…"}</Mono>
      </Row>
      <Row label={t("sampling")}>
        <Mono>
          {t("samplingValue", {
            temp: r ? r.llm_temperature.toFixed(2) : "—",
            topP: r ? r.llm_top_p.toFixed(2) : "—",
          })}
        </Mono>
      </Row>
      <Row label={t("embedding")}>
        <Mono>{r?.embedding_model ?? "…"}</Mono>
      </Row>
      <Row label={t("ocr")}>
        <Mono>{r?.ocr_engine ?? "…"}</Mono>
      </Row>
      <Row label={t("vectorBackend")}>
        <Mono>{r?.vector_backend ?? "…"}</Mono>
      </Row>
      {probe && (
        <Row label={t("lastProbe")}>
          <span className="inline-flex flex-wrap items-center justify-end gap-2">
            <StatusPill tone={probe.ok ? "success" : "danger"}>
              {probe.ok ? t("reachable") : t("unreachable")}
            </StatusPill>
            <span className="text-[11px] text-text-muted">
              {probe.latency_ms}ms
            </span>
            {probe.ok && probe.models.length > 0 && (
              <span className="text-[11px] text-text-muted">
                {probe.models.length === 1
                  ? t("modelsCount", { count: probe.models.length })
                  : t("modelsCountPlural", { count: probe.models.length })}
              </span>
            )}
            {!probe.ok && probe.error && (
              <span className="block w-full text-right text-[11px] text-status-danger">
                {probe.error}
              </span>
            )}
          </span>
        </Row>
      )}
    </Section>
  );
}
