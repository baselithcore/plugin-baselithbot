"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Database, Loader2, RefreshCw, Save } from "lucide-react";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";
import {
  getRetention,
  getStorageStats,
  setRetentionDays,
  type RuntimeInfo,
} from "@/lib/api/system";
import { Mono, Row, Section, StatusPill, bytesHuman } from "./SettingsShared";

export function StorageCard({
  runtime,
  isAdmin,
}: {
  runtime?: RuntimeInfo;
  isAdmin: boolean;
}) {
  const t = useTranslations("settings.storage");
  const qc = useQueryClient();
  const stats = useQuery({
    queryKey: ["system", "storage"],
    queryFn: getStorageStats,
  });
  const retention = useQuery({
    queryKey: ["system", "retention"],
    queryFn: getRetention,
  });

  const [days, setDays] = useState<number>(365);
  const [editing, setEditing] = useState(false);

  useEffect(() => {
    if (retention.data) setDays(retention.data.days);
  }, [retention.data]);

  const retMut = useMutation({
    mutationFn: (d: number) => setRetentionDays(d),
    onSuccess: () => {
      toast.success(t("toastUpdated"));
      setEditing(false);
      qc.invalidateQueries({ queryKey: ["system", "retention"] });
      qc.invalidateQueries({ queryKey: ["system", "runtime"] });
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const s = stats.data;

  return (
    <Section
      title={t("title")}
      icon={Database}
      actions={
        <Button
          size="sm"
          variant="ghost"
          onClick={() => {
            stats.refetch();
            retention.refetch();
          }}
          disabled={stats.isFetching}
        >
          {stats.isFetching ? (
            <Loader2 size={13} className="animate-spin" />
          ) : (
            <RefreshCw size={13} />
          )}
          {t("refresh")}
        </Button>
      }
    >
      <Row label={t("vectorDb")}>
        <Mono>
          {runtime?.vector_backend ?? "…"} · {runtime?.db_backend ?? "…"}
        </Mono>
      </Row>
      <Row label={t("database")}>
        <span className="inline-flex flex-wrap items-center justify-end gap-2">
          <Mono>{s ? bytesHuman(s.db_size_bytes) : "…"}</Mono>
          {s && (
            <span className="text-[11px] text-text-muted">· {s.db_path}</span>
          )}
        </span>
      </Row>
      <Row label={t("vectorStore")}>
        <span className="inline-flex flex-wrap items-center justify-end gap-2">
          <Mono>{s ? bytesHuman(s.chroma_size_bytes) : "…"}</Mono>
          {s && (
            <span className="text-[11px] text-text-muted">
              · {s.chroma_path}
            </span>
          )}
        </span>
      </Row>
      <Row label={t("storageRoot")}>
        <Mono>{s ? bytesHuman(s.storage_size_bytes) : "…"}</Mono>
      </Row>
      <Row label={t("documents")}>
        <Mono>
          {s
            ? t("documentsValue", {
                docs: s.documents,
                chunks: s.chunks,
                reports: s.reports,
              })
            : "…"}
        </Mono>
      </Row>
      <Row label={t("auditUsers")}>
        <Mono>
          {s
            ? t("auditUsersValue", { audit: s.audit_entries, users: s.users })
            : "…"}
        </Mono>
      </Row>
      <Row label={t("retention")}>
        {editing && isAdmin ? (
          <span className="inline-flex items-center justify-end gap-2">
            <input
              type="number"
              min={1}
              max={3650}
              value={days}
              onChange={(e) => setDays(Number(e.target.value))}
              className="w-24 h-8 px-2 bg-bg-canvas border border-border rounded-md text-sm text-right outline-none focus:border-status-info/60 focus:ring-2 focus:ring-status-info/20 transition-colors"
            />
            <span className="text-[11px] text-text-muted">{t("days")}</span>
            <Button
              size="sm"
              variant="primary"
              disabled={retMut.isPending}
              onClick={() => retMut.mutate(days)}
            >
              {retMut.isPending ? (
                <Loader2 size={13} className="animate-spin" />
              ) : (
                <Save size={13} />
              )}
              {t("save")}
            </Button>
            <Button
              size="sm"
              variant="ghost"
              onClick={() => {
                if (retention.data) setDays(retention.data.days);
                setEditing(false);
              }}
            >
              {t("cancel")}
            </Button>
          </span>
        ) : (
          <span className="inline-flex flex-wrap items-center justify-end gap-2">
            <Mono>
              {retention.data
                ? t("daysValue", { days: retention.data.days })
                : "…"}
            </Mono>
            {retention.data && (
              <StatusPill
                tone={retention.data.source === "override" ? "info" : "muted"}
              >
                {retention.data.source}
              </StatusPill>
            )}
            {isAdmin && (
              <Button
                size="sm"
                variant="ghost"
                onClick={() => setEditing(true)}
              >
                {t("edit")}
              </Button>
            )}
          </span>
        )}
      </Row>
    </Section>
  );
}
