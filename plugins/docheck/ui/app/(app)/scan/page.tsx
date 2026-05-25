"use client";

import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Radar, ShieldCheck } from "lucide-react";
import { useTranslations } from "next-intl";
import {
  analyzeDocument,
  getReportSummary,
  listDocuments,
  listPolicies,
  uploadDocument,
  type Finding,
  type Report,
  type Severity,
} from "@/lib/api";
import { TopBar } from "@/components/TopBar";
import { useAppStore } from "@/lib/store";
import { useLocaleStore } from "@/lib/i18n/store";
import { FindingDetailDrawer } from "@/components/findings/FindingDetailDrawer";
import { ReasoningDrawer } from "@/components/reasoning/ReasoningDrawer";
import { AskModal } from "@/components/findings/AskModal";
import { IntakeCard } from "@/components/scan/IntakeCard";
import { PolicyCard } from "@/components/scan/PolicyCard";
import { OptionsCard } from "@/components/scan/OptionsCard";
import { RunCard } from "@/components/scan/RunCard";
import { VerdictCard } from "@/components/scan/VerdictCard";
import { ResultsCard } from "@/components/scan/ResultsCard";
import {
  DEFAULT_PROFILE,
  FLOOR_RANK,
  type ScanProfile,
} from "@/components/scan/types";

type Phase = "idle" | "uploading" | "analyzing" | "done" | "error";

export default function ScanPage() {
  const t = useTranslations("scan");
  const [file, setFile] = useState<File | null>(null);
  const [pickedDocId, setPickedDocId] = useState<string | null>(null);
  const [policyIds, setPolicyIds] = useState<string[]>([]);
  const [profile, setProfile] = useState<ScanProfile>(DEFAULT_PROFILE);
  const [report, setReport] = useState<Report | null>(null);
  const [phase, setPhase] = useState<Phase>("idle");
  const [error, setError] = useState<string | null>(null);

  const policies = useQuery({
    queryKey: ["policies"],
    queryFn: listPolicies,
    staleTime: 60_000,
  });
  const docs = useQuery({
    queryKey: ["recent-docs"],
    queryFn: () => listDocuments(20),
    staleTime: 30_000,
  });

  useEffect(() => {
    if (policyIds.length === 0 && policies.data) {
      const active = policies.data
        .filter((p) => p.active && !p.system)
        .map((p) => p.id);
      if (active.length) setPolicyIds(active);
    }
  }, [policies.data, policyIds.length]);

  const setCurrentReport = useAppStore((s) => s.setCurrentReport);

  useEffect(() => {
    setCurrentReport(report);
  }, [report, setCurrentReport]);

  const locale = useLocaleStore((s) => s.locale);
  const summary = useMutation({
    mutationFn: (reportId: string) => getReportSummary(reportId, locale),
  });

  const run = useMutation({
    mutationFn: async () => {
      setError(null);
      summary.reset();
      let docId = pickedDocId;
      if (file) {
        setPhase("uploading");
        const up = await uploadDocument(file);
        docId = up.id;
      }
      if (!docId) throw new Error(t("run.errorPickDoc"));
      setPhase("analyzing");
      const rep = await analyzeDocument(docId, policyIds, {
        lang: profile.lang || undefined,
      });
      setReport(rep);
      setPhase("done");
      try {
        await summary.mutateAsync(rep.report_id);
      } catch {
        /* non-fatal */
      }
      return rep;
    },
    onError: (e: Error) => {
      setError(e.message || t("run.errorScanFailed"));
      setPhase("error");
    },
  });

  const filtered = useMemo<Finding[]>(() => {
    if (!report) return [];
    const minRank = FLOOR_RANK[profile.severityFloor as Severity];
    return report.findings.filter((f) => {
      if (!profile.includePass && f.severity === "PASS") return false;
      if (FLOOR_RANK[f.severity] < minRank) return false;
      if (f.confidence < profile.confidenceMin) return false;
      return true;
    });
  }, [report, profile]);

  const canRun =
    (file !== null || pickedDocId !== null) &&
    policyIds.length > 0 &&
    phase !== "analyzing" &&
    phase !== "uploading";

  const onReset = () => {
    setFile(null);
    setPickedDocId(null);
    setReport(null);
    setPhase("idle");
    setError(null);
    summary.reset();
  };

  return (
    <div className="h-screen flex flex-col">
      <TopBar />
      <main className="flex-1 overflow-auto bg-bg-canvas">
        <div className="mx-auto max-w-7xl px-6 lg:px-8 py-7">
          <ScanHeader />

          <section className="mt-6 grid gap-4 lg:grid-cols-3">
            <IntakeCard
              file={file}
              onFile={setFile}
              pickedDocId={pickedDocId}
              onPick={setPickedDocId}
              docs={docs.data ?? []}
              docsLoading={docs.isLoading}
            />
            <PolicyCard
              policies={policies.data ?? []}
              loading={policies.isLoading}
              selected={policyIds}
              onChange={setPolicyIds}
            />
            <OptionsCard profile={profile} onChange={setProfile} />
          </section>

          <section className="sticky top-2 z-10 mt-4">
            <RunCard
              canRun={canRun}
              phase={phase}
              error={error}
              onRun={() => run.mutate()}
              onReset={onReset}
            />
          </section>

          <section className="mt-6 grid gap-5 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.4fr)]">
            <VerdictCard
              report={report}
              phase={phase}
              summary={summary.data ?? null}
              summaryLoading={summary.isPending}
              summaryError={summary.error?.message ?? null}
              onRetrySummary={() => report && summary.mutate(report.report_id)}
            />
            <ResultsCard
              report={report}
              findings={filtered}
              profile={profile}
              phase={phase}
            />
          </section>
        </div>
      </main>
      <FindingDetailDrawer />
      <ReasoningDrawer />
      <AskModal />
    </div>
  );
}

function ScanHeader() {
  const t = useTranslations("scan.header");
  return (
    <div className="flex items-center justify-between gap-6">
      <div>
        <div className="inline-flex items-center gap-2 rounded-md border border-border bg-bg-panel-elev px-2.5 py-1 text-[11px] font-medium text-text-secondary">
          <Radar size={12} className="text-status-info" />
          {t("eyebrow")}
        </div>
        <h1 className="mt-3 text-2xl font-semibold tracking-tight">
          {t("title")}
        </h1>
        <p className="mt-1.5 text-sm text-text-muted max-w-2xl">
          {t("description")}
        </p>
      </div>
      <div className="hidden md:flex items-center gap-2 text-[11px] text-text-muted">
        <ShieldCheck size={13} className="text-status-success" />
        {t("footer")}
      </div>
    </div>
  );
}
