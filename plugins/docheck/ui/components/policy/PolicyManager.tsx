"use client";

import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import {
  CheckCircle2,
  FileText,
  Filter,
  Import,
  Search,
  ShieldCheck,
  SlidersHorizontal,
  X,
} from "lucide-react";
import { listPolicies, type PolicyRow } from "@/lib/api";
import { useAppStore } from "@/lib/store";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/cn";
import { PolicySwitch } from "./PolicyToggleBoard";
import { PolicyManagerDetail } from "./PolicyManagerDetail";

type ScopeFilter = "all" | PolicyRow["scope"];

const SCOPE_IDS: ScopeFilter[] = [
  "all",
  "global_default",
  "eu",
  "world",
  "custom",
];

interface Props {
  open: boolean;
  onClose: () => void;
}

function useScopeLabel() {
  const t = useTranslations("policies.scope");
  return (s: PolicyRow["scope"] | "all"): string => {
    switch (s) {
      case "all":
        return t("all");
      case "global_default":
        return t("global_default");
      case "eu":
        return t("eu");
      case "world":
        return t("world");
      case "custom":
        return t("custom");
    }
  };
}

export function PolicyManager({ open, onClose }: Props) {
  const t = useTranslations("policies");
  const tManager = useTranslations("policies.manager");
  const scopeLabel = useScopeLabel();
  const [scope, setScope] = useState<ScopeFilter>("all");
  const [query, setQuery] = useState("");
  const [selectedRow, setSelectedRow] = useState<PolicyRow | null>(null);
  const selected = useAppStore((s) => s.selectedPolicies);
  const setSelected = useAppStore((s) => s.setSelectedPolicies);

  const policies = useQuery({
    queryKey: ["policies"],
    queryFn: listPolicies,
    enabled: open,
    staleTime: 60_000,
  });
  const rows = useMemo(() => policies.data ?? [], [policies.data]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return rows.filter((p) => {
      const matchesScope = scope === "all" || p.scope === scope;
      const matchesQuery =
        !q ||
        p.title.toLowerCase().includes(q) ||
        p.id.toLowerCase().includes(q) ||
        scopeLabel(p.scope).toLowerCase().includes(q);
      return matchesScope && matchesQuery;
    });
  }, [query, rows, scope, scopeLabel]);

  const visibleSelected = filtered.filter((p) =>
    selected.includes(p.id),
  ).length;
  const selectedRows = rows.filter((p) => selected.includes(p.id));
  const selectedRules = selectedRows.reduce((sum, p) => sum + p.rule_count, 0);
  const allVisibleSelected =
    filtered.length > 0 && visibleSelected === filtered.length;

  useEffect(() => {
    if (!open) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  useEffect(() => {
    if (!selectedRow && rows.length > 0) {
      const firstSelected = rows.find((p) => selected.includes(p.id));
      setSelectedRow(firstSelected ?? rows[0]);
    }
  }, [rows, selected, selectedRow]);

  if (!open) return null;

  function toggle(id: string) {
    setSelected(
      selected.includes(id)
        ? selected.filter((p) => p !== id)
        : [...selected, id],
    );
  }

  function selectVisible() {
    const ids = new Set(selected);
    filtered.forEach((p) => ids.add(p.id));
    setSelected(Array.from(ids));
  }

  function clearVisible() {
    const visible = new Set(filtered.map((p) => p.id));
    setSelected(selected.filter((id) => !visible.has(id)));
  }

  function clearAll() {
    setSelected([]);
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-bg-canvas/75 p-4 backdrop-blur-sm animate-fade-in"
      role="dialog"
      aria-modal
      aria-labelledby="policy-manager-title"
      onClick={onClose}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className="flex h-[min(780px,92vh)] w-full max-w-6xl flex-col overflow-hidden rounded-xl border border-border surface-elev shadow-popover animate-slide-up"
      >
        <header className="flex items-center justify-between gap-4 border-b border-border px-5 py-4">
          <div className="flex min-w-0 items-center gap-3">
            <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border border-status-info/35 bg-status-info/10 text-status-info">
              <SlidersHorizontal size={18} />
            </span>
            <div className="min-w-0">
              <div className="flex items-center gap-2 text-[10px] uppercase tracking-[0.18em] text-text-muted">
                {tManager("eyebrow")}
              </div>
              <h2
                id="policy-manager-title"
                className="mt-1 truncate text-base font-semibold tracking-tight"
              >
                {tManager("title")}
              </h2>
            </div>
          </div>

          <div className="hidden min-w-[360px] grid-cols-3 gap-2 md:grid">
            <HeaderStat
              label={t("stats.selected")}
              value={String(selected.length)}
              tone="success"
            />
            <HeaderStat
              label={t("stats.rulesMatch")}
              value={String(selectedRules)}
              tone="info"
            />
            <HeaderStat
              label={t("stats.visibleOn")}
              value={`${visibleSelected}/${filtered.length}`}
              tone="warning"
            />
          </div>

          <button
            type="button"
            onClick={onClose}
            aria-label={t("close")}
            className="rounded-md p-2 text-text-muted transition-colors hover:bg-bg-panel-elev hover:text-text-primary ring-focus"
          >
            <X size={18} />
          </button>
        </header>

        <div className="grid min-h-0 flex-1 grid-cols-1 lg:grid-cols-[minmax(430px,0.9fr)_1.1fr]">
          <aside className="flex min-h-0 flex-col border-r border-border bg-bg-panel-soft">
            <div className="border-b border-border p-4">
              <label className="flex h-10 items-center gap-2 rounded-md border border-border bg-bg-canvas px-3 text-xs text-text-muted transition-colors focus-within:border-status-info/60 focus-within:ring-2 focus-within:ring-status-info/20">
                <Search size={14} />
                <input
                  autoFocus
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder={t("searchManager")}
                  className="min-w-0 flex-1 bg-transparent text-text-primary outline-none placeholder:text-text-muted"
                />
              </label>

              <div className="mt-3 flex flex-wrap items-center gap-2">
                <span className="inline-flex items-center gap-1.5 text-[10px] uppercase tracking-[0.14em] text-text-muted">
                  <Filter size={11} />
                  {tManager("scopeLabel")}
                </span>
                {SCOPE_IDS.map((id) => (
                  <button
                    key={id}
                    type="button"
                    onClick={() => setScope(id)}
                    className={cn(
                      "h-7 rounded-md border px-2.5 text-xs transition-colors ring-focus",
                      scope === id
                        ? "border-status-info/45 bg-status-info/10 text-status-info"
                        : "border-border bg-bg-panel text-text-secondary hover:border-border-strong hover:text-text-primary",
                    )}
                  >
                    {scopeLabel(id)}
                  </button>
                ))}
              </div>

              <div className="mt-3 flex gap-2">
                <Button
                  type="button"
                  variant="secondary"
                  size="sm"
                  onClick={allVisibleSelected ? clearVisible : selectVisible}
                >
                  <CheckCircle2 size={13} />
                  {allVisibleSelected
                    ? t("turnOffVisible")
                    : t("turnOnVisible")}
                </Button>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={clearAll}
                >
                  {tManager("clearAll")}
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  className="ml-auto"
                >
                  <Import size={13} />
                  {tManager("import")}
                </Button>
              </div>
            </div>

            <div className="min-h-0 flex-1 overflow-auto p-3">
              {policies.isLoading && (
                <div className="space-y-2">
                  {Array.from({ length: 6 }).map((_, i) => (
                    <Skeleton key={i} className="h-[84px]" />
                  ))}
                </div>
              )}

              <div className="space-y-2">
                {filtered.map((policy) => {
                  const isChecked = selected.includes(policy.id);
                  const isOpen =
                    selectedRow?.id === policy.id &&
                    selectedRow.version === policy.version;
                  return (
                    <div
                      key={`${policy.id}@${policy.version}`}
                      role="button"
                      tabIndex={0}
                      onClick={() => setSelectedRow(policy)}
                      onKeyDown={(event) => {
                        if (event.key === "Enter" || event.key === " ") {
                          event.preventDefault();
                          setSelectedRow(policy);
                        }
                      }}
                      className={cn(
                        "w-full cursor-pointer rounded-lg border px-3 py-3 text-left transition-all ring-focus",
                        isOpen
                          ? "border-status-info/55 bg-bg-panel-elev shadow-[inset_3px_0_0_rgba(14,165,233,0.85)]"
                          : "border-border bg-bg-canvas hover:border-border-strong hover:bg-bg-panel",
                      )}
                    >
                      <div className="flex items-center gap-3">
                        <span
                          className={cn(
                            "flex h-10 w-10 shrink-0 items-center justify-center rounded-md border",
                            isChecked
                              ? "border-status-success/35 bg-status-success/10 text-status-success"
                              : "border-border bg-bg-panel text-text-muted",
                          )}
                        >
                          {isChecked ? (
                            <ShieldCheck size={17} />
                          ) : (
                            <FileText size={17} />
                          )}
                        </span>

                        <span className="min-w-0 flex-1">
                          <span className="flex min-w-0 items-center gap-2">
                            <span className="truncate text-sm font-semibold text-text-primary">
                              {policy.title}
                            </span>
                            <span className="shrink-0 rounded border border-border bg-bg-panel px-1.5 py-0.5 text-[10px] uppercase text-text-muted">
                              {scopeLabel(policy.scope)}
                            </span>
                          </span>
                          <span className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-1 text-[11px] text-text-muted">
                            <span className="font-mono">
                              {policy.id}@{policy.version}
                            </span>
                            <span>
                              {tManager("rulesCount", {
                                count: policy.rule_count,
                              })}
                            </span>
                            <span>{policy.lang.toUpperCase()}</span>
                          </span>
                        </span>

                        <PolicySwitch
                          checked={isChecked}
                          onToggle={() => toggle(policy.id)}
                          label={t("togglePolicy", {
                            action: isChecked ? t("deactivate") : t("activate"),
                            title: policy.title,
                          })}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>

              {!policies.isLoading && filtered.length === 0 && (
                <EmptyState
                  icon={Search}
                  title={t("noResultsTitle")}
                  description={t("noResultsDesc")}
                  className="mt-2 min-h-[240px]"
                />
              )}
            </div>
          </aside>

          <PolicyManagerDetail
            open={open}
            selectedRow={selectedRow}
            selected={selected}
            onToggle={toggle}
          />
        </div>

        <footer className="flex flex-col gap-3 border-t border-border px-5 py-3 md:flex-row md:items-center md:justify-between">
          <div className="min-w-0 text-[11px] text-text-muted">
            {tManager("footerMatch")}{" "}
            <span className="font-mono text-text-secondary">
              {selected.length}
            </span>{" "}
            {tManager("footerPolicy")}
            {selected.length > 0 && (
              <span className="ml-2 hidden truncate text-text-faint md:inline">
                {selected.slice(0, 4).join(" · ")}
                {selected.length > 4 ? " · ..." : ""}
              </span>
            )}
          </div>
          <div className="flex justify-end gap-2">
            <Button variant="ghost" size="sm" onClick={onClose}>
              {tManager("cancel")}
            </Button>
            <Button variant="primary" size="sm" onClick={onClose}>
              {tManager("apply")}
            </Button>
          </div>
        </footer>
      </div>
    </div>
  );
}

function HeaderStat({
  label,
  value,
  tone,
}: {
  label: string;
  value: string;
  tone: "success" | "warning" | "info";
}) {
  const toneClass = {
    success: "text-status-success",
    warning: "text-status-warning",
    info: "text-status-info",
  }[tone];
  return (
    <div className="rounded-md border border-border bg-bg-canvas px-3 py-2">
      <div className="text-[10px] uppercase tracking-wide text-text-muted">
        {label}
      </div>
      <div
        className={cn("mt-0.5 text-base font-semibold tabular-nums", toneClass)}
      >
        {value}
      </div>
    </div>
  );
}
