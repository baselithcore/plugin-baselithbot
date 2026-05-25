"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import {
  CheckCircle2,
  FileText,
  Layers,
  Upload,
  type LucideIcon,
} from "lucide-react";
import type { DocumentRow } from "@/lib/api";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/cn";
import { StepHeader, TabBtn } from "./StepHeader";

interface Props {
  file: File | null;
  onFile: (f: File | null) => void;
  pickedDocId: string | null;
  onPick: (id: string | null) => void;
  docs: DocumentRow[];
  docsLoading: boolean;
}

export function IntakeCard({
  file,
  onFile,
  pickedDocId,
  onPick,
  docs,
  docsLoading,
}: Props) {
  const t = useTranslations("scan.intake");
  const [tab, setTab] = useState<"upload" | "vault">("upload");
  return (
    <Card>
      <CardContent className="pt-5">
        <StepHeader
          idx={1}
          icon={FileText}
          title={t("title")}
          hint={t("hint")}
        />
        <div className="flex rounded-md border border-border bg-bg-canvas p-0.5 mb-3">
          <TabBtn
            active={tab === "upload"}
            onClick={() => {
              setTab("upload");
              onPick(null);
            }}
            icon={Upload}
            label={t("tabUpload")}
          />
          <TabBtn
            active={tab === "vault"}
            onClick={() => {
              setTab("vault");
              onFile(null);
            }}
            icon={Layers}
            label={t("tabVault")}
          />
        </div>

        {tab === "upload" ? (
          <UploadBox file={file} onFile={onFile} />
        ) : (
          <VaultList
            docs={docs}
            loading={docsLoading}
            pickedDocId={pickedDocId}
            onPick={onPick}
          />
        )}
      </CardContent>
    </Card>
  );
}

function UploadBox({
  file,
  onFile,
}: {
  file: File | null;
  onFile: (f: File | null) => void;
}) {
  const t = useTranslations("scan.intake");
  return (
    <label
      className={cn(
        "block rounded-lg border border-dashed bg-bg-panel-soft p-4 cursor-pointer transition-colors",
        file
          ? "border-status-success/50 bg-status-success/5"
          : "border-border hover:border-status-info/50",
      )}
    >
      <input
        type="file"
        className="sr-only"
        accept=".pdf,.docx,.xlsx,.md,.txt"
        onChange={(e) => onFile(e.target.files?.[0] ?? null)}
      />
      <div className="flex items-center gap-3">
        <div
          className={cn(
            "flex h-9 w-9 items-center justify-center rounded-md border",
            file
              ? "border-status-success/40 bg-status-success/10 text-status-success"
              : "border-border bg-bg-panel text-status-info",
          )}
        >
          {file ? <CheckCircle2 size={16} /> : <Upload size={16} />}
        </div>
        <div className="min-w-0 flex-1">
          {file ? (
            <>
              <div className="truncate text-sm font-medium">{file.name}</div>
              <div className="text-[11px] text-text-muted">
                {t("ready", { size: (file.size / 1024).toFixed(1) })}
              </div>
            </>
          ) : (
            <>
              <div className="text-sm font-medium">{t("drop")}</div>
              <div className="text-[11px] text-text-muted">{t("formats")}</div>
            </>
          )}
        </div>
      </div>
    </label>
  );
}

function VaultList({
  docs,
  loading,
  pickedDocId,
  onPick,
}: {
  docs: DocumentRow[];
  loading: boolean;
  pickedDocId: string | null;
  onPick: (id: string | null) => void;
}) {
  const t = useTranslations("scan.intake");
  if (loading) {
    return (
      <div className="rounded-lg border border-border bg-bg-canvas p-3 space-y-2">
        {Array.from({ length: 3 }).map((_, i) => (
          <Skeleton key={i} className="h-10" />
        ))}
      </div>
    );
  }
  if (docs.length === 0) {
    return (
      <div className="rounded-lg border border-border bg-bg-canvas p-4 text-center text-xs text-text-muted">
        {t("vaultEmpty")}
      </div>
    );
  }
  return (
    <div className="rounded-lg border border-border bg-bg-canvas max-h-64 overflow-auto divide-y divide-border">
      {docs.map((d) => (
        <button
          key={d.id}
          type="button"
          onClick={() => onPick(d.id)}
          className={cn(
            "w-full flex items-center gap-3 px-3 py-2.5 text-left hover:bg-bg-panel-elev transition-colors",
            pickedDocId === d.id && "bg-status-info/10",
          )}
        >
          <FileText
            size={14}
            className={
              pickedDocId === d.id ? "text-status-info" : "text-text-muted"
            }
          />
          <div className="min-w-0 flex-1">
            <div className="truncate text-xs font-medium">{d.filename}</div>
            <div className="font-mono text-[10px] text-text-muted truncate">
              {d.id} · {d.pages ?? "?"}p
              {d.doc_type ? ` · ${t(`docType.${d.doc_type}`)}` : ""}
            </div>
          </div>
          {pickedDocId === d.id && (
            <CheckCircle2 size={13} className="text-status-info shrink-0" />
          )}
        </button>
      ))}
    </div>
  );
}

// keep type re-export for tree-shake friendly access
export type { LucideIcon };
