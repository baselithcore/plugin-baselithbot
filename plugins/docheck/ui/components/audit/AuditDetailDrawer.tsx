"use client";

import { useQuery } from "@tanstack/react-query";
import { Download, ShieldCheck, ShieldOff, X } from "lucide-react";
import { useFormatter, useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { getAuditEntry } from "@/lib/api/audit";

export function AuditDetailDrawer({
  seq,
  onClose,
}: {
  seq: number;
  onClose: () => void;
}) {
  const t = useTranslations("audit.detail");
  const fmt = useFormatter();
  const detail = useQuery({
    queryKey: ["audit-detail", seq],
    queryFn: () => getAuditEntry(seq),
  });
  const copy = (s: string) => navigator.clipboard.writeText(s).catch(() => {});

  return (
    <div
      className="fixed inset-0 z-40 flex justify-end bg-black/40 animate-fade-in"
      onClick={onClose}
    >
      <div
        className="h-full w-full max-w-md overflow-auto border-l border-border bg-bg-panel p-5 shadow-panel"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-semibold">{t("title", { seq })}</h3>
          <button
            onClick={onClose}
            className="text-text-muted hover:text-text-primary"
          >
            <X size={16} />
          </button>
        </div>
        {detail.isLoading && <Skeleton className="h-40" />}
        {detail.error && (
          <div className="text-xs text-status-danger">
            {t("loadFailed", { error: (detail.error as Error).message })}
          </div>
        )}
        {detail.data && (
          <div className="space-y-3 text-xs">
            <Row label={t("status")}>
              {detail.data.valid ? (
                <span className="inline-flex items-center gap-1.5 text-status-success">
                  <ShieldCheck size={12} /> {t("validSignature")}
                </span>
              ) : (
                <span className="inline-flex items-center gap-1.5 text-status-danger">
                  <ShieldOff size={12} /> {detail.data.error ?? t("invalid")}
                </span>
              )}
            </Row>
            <Row label={t("timestamp")}>
              {fmt.dateTime(new Date(detail.data.ts), {
                dateStyle: "medium",
                timeStyle: "medium",
              })}
            </Row>
            <Row label={t("user")}>
              {detail.data.user_email ?? detail.data.user_id ?? "—"}
            </Row>
            <Row label={t("action")}>
              <span className="font-mono">{detail.data.action}</span>
            </Row>
            <Row label={t("resource")}>
              <span className="font-mono break-all">
                {detail.data.resource ?? "—"}
              </span>
            </Row>
            <Hash
              label={t("payloadHash")}
              value={detail.data.payload_hash}
              onCopy={copy}
              copyTitle={t("copyTitle")}
            />
            <Hash
              label={t("prevHash")}
              value={detail.data.prev_hash}
              onCopy={copy}
              copyTitle={t("copyTitle")}
            />
            <Hash
              label={t("entryHash")}
              value={detail.data.entry_hash}
              onCopy={copy}
              copyTitle={t("copyTitle")}
            />
            <Hash
              label={t("signature")}
              value={detail.data.signature}
              onCopy={copy}
              copyTitle={t("copyTitle")}
            />
            <Button
              size="sm"
              variant="outline"
              className="w-full mt-2"
              onClick={() => downloadJson(seq, detail.data)}
            >
              <Download size={13} /> {t("downloadJson")}
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}

function downloadJson(seq: number, data: unknown) {
  const blob = new Blob([JSON.stringify(data, null, 2)], {
    type: "application/json",
  });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `audit-entry-${seq}.json`;
  a.click();
  URL.revokeObjectURL(url);
}

function Row({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div className="grid grid-cols-[110px_1fr] gap-3 items-baseline">
      <span className="text-[10px] uppercase tracking-wide text-text-muted">
        {label}
      </span>
      <span>{children}</span>
    </div>
  );
}

function Hash({
  label,
  value,
  onCopy,
  copyTitle,
}: {
  label: string;
  value: string;
  onCopy: (s: string) => void;
  copyTitle: string;
}) {
  return (
    <div>
      <div className="text-[10px] uppercase tracking-wide text-text-muted mb-1">
        {label}
      </div>
      <button
        onClick={() => onCopy(value)}
        className="w-full text-left rounded-md border border-border bg-bg-canvas px-2 py-1.5 font-mono text-[10px] break-all hover:border-border-strong"
        title={copyTitle}
      >
        {value}
      </button>
    </div>
  );
}
