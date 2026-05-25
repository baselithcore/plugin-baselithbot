"use client";

import { useMemo, useState } from "react";
import { CheckCircle2, Lock, Scale } from "lucide-react";
import { useTranslations } from "next-intl";
import type { PolicyRow } from "@/lib/api";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/cn";
import { StepHeader } from "./StepHeader";

interface Props {
  policies: PolicyRow[];
  loading: boolean;
  selected: string[];
  onChange: (v: string[]) => void;
}

export function PolicyCard({ policies, loading, selected, onChange }: Props) {
  const t = useTranslations("scan.policy");
  const [filter, setFilter] = useState("");
  const list = useMemo(
    () =>
      policies.filter(
        (p) =>
          !filter ||
          p.id.toLowerCase().includes(filter.toLowerCase()) ||
          p.title.toLowerCase().includes(filter.toLowerCase()),
      ),
    [policies, filter],
  );
  const toggle = (id: string) => {
    const target = policies.find((p) => p.id === id);
    if (target?.system) return;
    onChange(
      selected.includes(id)
        ? selected.filter((x) => x !== id)
        : [...selected, id],
    );
  };
  const allActive = policies
    .filter((p) => p.active && !p.system)
    .map((p) => p.id);

  return (
    <Card>
      <CardContent className="pt-5">
        <StepHeader
          idx={2}
          icon={Scale}
          title={t("title")}
          hint={t("hint", {
            selected: selected.length,
            total: policies.length,
          })}
        />
        <div className="flex items-center gap-2 mb-3">
          <input
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            placeholder={t("filter")}
            className="flex-1 rounded-md border border-border bg-bg-canvas px-3 py-1.5 text-xs placeholder:text-text-muted ring-focus"
          />
          <Button size="sm" variant="ghost" onClick={() => onChange(allActive)}>
            {t("allActive")}
          </Button>
          <Button size="sm" variant="ghost" onClick={() => onChange([])}>
            {t("clear")}
          </Button>
        </div>
        <div className="rounded-lg border border-border bg-bg-canvas max-h-56 overflow-auto divide-y divide-border">
          {loading ? (
            <div className="p-3 space-y-2">
              {Array.from({ length: 3 }).map((_, i) => (
                <Skeleton key={i} className="h-9" />
              ))}
            </div>
          ) : list.length === 0 ? (
            <div className="p-4 text-center text-xs text-text-muted">
              {t("noMatches")}
            </div>
          ) : (
            list.map((p) => (
              <PolicyRowItem
                key={`${p.id}@${p.version}`}
                p={p}
                on={p.system ? true : selected.includes(p.id)}
                toggle={toggle}
              />
            ))
          )}
        </div>
      </CardContent>
    </Card>
  );
}

function PolicyRowItem({
  p,
  on,
  toggle,
}: {
  p: PolicyRow;
  on: boolean;
  toggle: (id: string) => void;
}) {
  const t = useTranslations("scan.policy");
  const sys = !!p.system;
  return (
    <button
      type="button"
      onClick={() => toggle(p.id)}
      disabled={sys}
      title={
        sys ? "Policy di sistema — sempre attiva, non modificabile" : undefined
      }
      className={cn(
        "w-full flex items-center gap-3 px-3 py-2 text-left hover:bg-bg-panel-elev transition-colors",
        on && "bg-status-info/5",
        sys && "cursor-not-allowed opacity-95",
      )}
    >
      <span
        className={cn(
          "flex h-4 w-4 shrink-0 items-center justify-center rounded border transition-colors",
          on ? "border-status-info bg-status-info text-white" : "border-border",
        )}
      >
        {sys ? <Lock size={10} /> : on && <CheckCircle2 size={11} />}
      </span>
      <div className="min-w-0 flex-1">
        <div className="truncate text-xs font-medium">{p.title}</div>
        <div className="font-mono text-[10px] text-text-muted">
          {p.id} · v{p.version} · {t("rules", { count: p.rule_count })}
        </div>
      </div>
      {sys ? (
        <span className="shrink-0 rounded-full border border-status-info/40 bg-status-info/10 px-1.5 py-0.5 text-[9px] uppercase tracking-wide text-status-info">
          Sistema
        </span>
      ) : (
        <span
          className={cn(
            "shrink-0 rounded-full border px-1.5 py-0.5 text-[9px] uppercase tracking-wide",
            p.active
              ? "border-status-success/40 text-status-success bg-status-success/10"
              : "border-border text-text-muted",
          )}
        >
          {p.active ? t("active") : t("idle")}
        </span>
      )}
    </button>
  );
}
