"use client";

import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";

export function CloneDialog({
  open,
  version,
  busy,
  onChange,
  onClose,
  onConfirm,
}: {
  open: boolean;
  version: string;
  busy: boolean;
  onChange: (v: string) => void;
  onClose: () => void;
  onConfirm: () => void;
}) {
  const t = useTranslations("policies.clone");
  if (!open) return null;
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-bg-canvas/70 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className="w-[min(420px,92vw)] rounded-xl border border-border surface-elev p-5 shadow-popover"
      >
        <div className="text-[10px] uppercase tracking-[0.2em] text-text-muted">
          {t("eyebrow")}
        </div>
        <h3 className="mt-1 text-sm font-semibold">{t("title")}</h3>
        <p className="mt-1 text-xs text-text-muted">{t("desc")}</p>
        <input
          autoFocus
          value={version}
          onChange={(e) => onChange(e.target.value)}
          className="mt-4 h-9 w-full rounded-md border border-border bg-bg-canvas px-3 text-xs outline-none focus:border-status-info/60 focus:ring-2 focus:ring-status-info/20"
          placeholder={t("versionPlaceholder")}
        />
        <div className="mt-5 flex justify-end gap-2">
          <Button size="sm" variant="ghost" onClick={onClose} disabled={busy}>
            {t("cancel")}
          </Button>
          <Button
            size="sm"
            variant="primary"
            onClick={onConfirm}
            disabled={busy || !version.trim()}
          >
            {t("confirm")}
          </Button>
        </div>
      </div>
    </div>
  );
}

export function UrlIngestDialog({
  open,
  url,
  busy,
  onChange,
  onClose,
  onConfirm,
}: {
  open: boolean;
  url: string;
  busy: boolean;
  onChange: (v: string) => void;
  onClose: () => void;
  onConfirm: () => void;
}) {
  const t = useTranslations("policies.ingest");
  if (!open) return null;
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-bg-canvas/70 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className="w-[min(520px,92vw)] rounded-xl border border-border surface-elev p-5 shadow-popover"
      >
        <div className="text-[10px] uppercase tracking-[0.2em] text-text-muted">
          {t("fromUrlEyebrow")}
        </div>
        <h3 className="mt-1 text-sm font-semibold">{t("fromUrlTitle")}</h3>
        <p className="mt-1 text-xs text-text-muted">
          {t("fromUrlDesc")} <span className="font-semibold">{t("draft")}</span>
          .
        </p>
        <input
          autoFocus
          value={url}
          onChange={(e) => onChange(e.target.value)}
          placeholder={t("urlPlaceholder")}
          className="mt-4 h-9 w-full rounded-md border border-border bg-bg-canvas px-3 text-xs outline-none focus:border-status-info/60 focus:ring-2 focus:ring-status-info/20"
        />
        {busy && (
          <div className="mt-3">
            <div className="text-[10px] uppercase tracking-wide text-text-muted">
              {t("extracting")}
            </div>
            <Progress className="mt-1.5" value={0} indeterminate />
          </div>
        )}
        <div className="mt-5 flex justify-end gap-2">
          <Button size="sm" variant="ghost" onClick={onClose} disabled={busy}>
            {t("cancel")}
          </Button>
          <Button
            size="sm"
            variant="primary"
            onClick={onConfirm}
            disabled={busy || !url.trim()}
          >
            {busy ? t("extracting") : t("ingest")}
          </Button>
        </div>
      </div>
    </div>
  );
}
