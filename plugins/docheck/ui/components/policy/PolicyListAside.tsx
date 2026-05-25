"use client";

import {
  FileText,
  Globe,
  Plus,
  Scale,
  Search,
  Sparkles,
  Upload,
} from "lucide-react";
import type { RefObject } from "react";
import { useTranslations } from "next-intl";

import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import type { PolicyRow } from "@/lib/api";
import { cn } from "@/lib/cn";

import { Pill } from "./PolicyBits";

export type ScopeFilter = "all" | PolicyRow["scope"];

export const SCOPE_IDS: ScopeFilter[] = [
  "all",
  "global_default",
  "eu",
  "world",
  "custom",
];

function useScopeLabel() {
  const t = useTranslations("policies.scope");
  return (s: ScopeFilter): string => {
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

export interface PolicyListAsideProps {
  active: number;
  totalVersions: number;
  query: string;
  onQuery: (v: string) => void;
  scopeFilter: ScopeFilter;
  onScopeFilter: (s: ScopeFilter) => void;
  onCreate: () => void;
  onImportClick: () => void;
  onUrlIngestOpen: () => void;
  onIngestDocClick: () => void;
  importPending: boolean;
  ingestUrlPending: boolean;
  ingestDocPending: boolean;
  fileInputRef: RefObject<HTMLInputElement | null>;
  docInputRef: RefObject<HTMLInputElement | null>;
  onFilePicked: (e: React.ChangeEvent<HTMLInputElement>) => void;
  onDocPicked: (e: React.ChangeEvent<HTMLInputElement>) => void;
  isLoading: boolean;
  error: unknown;
  filtered: PolicyRow[];
  selected: PolicyRow | null;
  onSelect: (p: PolicyRow) => void;
}

export function PolicyListAside({
  active,
  totalVersions,
  query,
  onQuery,
  scopeFilter,
  onScopeFilter,
  onCreate,
  onImportClick,
  onUrlIngestOpen,
  onIngestDocClick,
  importPending,
  ingestUrlPending,
  ingestDocPending,
  fileInputRef,
  docInputRef,
  onFilePicked,
  onDocPicked,
  isLoading,
  error,
  filtered,
  selected,
  onSelect,
}: PolicyListAsideProps) {
  const t = useTranslations("policies.aside");
  const scopeLabel = useScopeLabel();
  return (
    <aside className="border-r border-border bg-bg-panel-soft overflow-hidden flex flex-col">
      <div className="border-b border-border p-5">
        <div className="flex items-center gap-2 text-[10px] uppercase tracking-[0.2em] text-text-muted">
          <Scale size={13} />
          {t("registry")}
        </div>
        <div className="mt-3 flex items-end justify-between">
          <div>
            <h1 className="text-xl font-semibold tracking-tight">
              {t("title")}
            </h1>
            <p className="mt-1 text-xs text-text-muted">
              {t("stats", { active, total: totalVersions })}
            </p>
          </div>
          <span className="rounded-md border border-status-info/30 bg-status-info/10 px-2 py-0.5 text-[10px] font-medium text-status-info">
            {t("versioned")}
          </span>
        </div>

        <label className="mt-4 flex h-9 items-center gap-2 rounded-md border border-border bg-bg-canvas px-3 text-xs text-text-muted">
          <Search size={14} />
          <input
            value={query}
            onChange={(e) => onQuery(e.target.value)}
            placeholder={t("searchPolicies")}
            className="min-w-0 flex-1 bg-transparent outline-none text-text-primary placeholder:text-text-muted"
          />
        </label>

        <div className="mt-3 flex flex-wrap gap-1 rounded-md border border-border bg-bg-canvas p-1">
          {SCOPE_IDS.map((id) => (
            <button
              key={id}
              type="button"
              onClick={() => onScopeFilter(id)}
              className={cn(
                "h-7 rounded px-2.5 text-[11px] transition-colors",
                scopeFilter === id
                  ? "bg-bg-panel-elev text-text-primary"
                  : "text-text-secondary hover:text-text-primary",
              )}
            >
              {scopeLabel(id)}
            </button>
          ))}
        </div>

        <div className="mt-3 flex flex-wrap gap-2">
          <Button size="sm" variant="primary" onClick={onCreate}>
            <Plus size={13} /> {t("new")}
          </Button>
          <Button
            size="sm"
            variant="outline"
            onClick={onImportClick}
            disabled={importPending}
          >
            <Upload size={13} /> {t("importYaml")}
          </Button>
          <Button
            size="sm"
            variant="outline"
            onClick={onUrlIngestOpen}
            disabled={ingestUrlPending}
          >
            <Globe size={13} /> {t("fromUrl")}
          </Button>
          <Button
            size="sm"
            variant="outline"
            onClick={onIngestDocClick}
            disabled={ingestDocPending}
            title={t("fromDocumentTitle")}
          >
            <Sparkles size={13} /> {t("fromDocument")}
          </Button>
          <input
            ref={fileInputRef}
            type="file"
            accept=".yaml,.yml,application/x-yaml,text/yaml"
            hidden
            onChange={onFilePicked}
          />
          <input
            ref={docInputRef}
            type="file"
            accept=".pdf,.docx,.xlsx,.md,.txt,.yaml,.yml"
            hidden
            onChange={onDocPicked}
          />
        </div>
      </div>

      <div className="flex-1 overflow-auto">
        {isLoading && (
          <div className="space-y-2 p-3">
            {Array.from({ length: 6 }).map((_, i) => (
              <Skeleton key={i} className="h-16" />
            ))}
          </div>
        )}
        {error ? (
          <div className="p-4">
            <EmptyState
              icon={Scale}
              title={t("loadError")}
              description={(error as Error).message}
            />
          </div>
        ) : null}
        {filtered.map((p) => {
          const sel = selected?.id === p.id && selected.version === p.version;
          return (
            <button
              key={`${p.id}@${p.version}`}
              type="button"
              onClick={() => onSelect(p)}
              className={cn(
                "relative w-full border-b border-border px-4 py-3 text-left transition-colors hover:bg-bg-panel-elev",
                sel && "bg-bg-panel-elev",
              )}
            >
              {sel && (
                <span className="absolute left-0 top-1/2 -translate-y-1/2 h-8 w-0.5 rounded-r bg-status-info shadow-[0_0_10px_rgba(47,123,255,0.7)]" />
              )}
              <div className="flex items-start gap-3">
                <span
                  className={cn(
                    "mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-md border bg-bg-canvas",
                    sel
                      ? "border-status-info/40 text-status-info"
                      : "border-border text-text-muted",
                  )}
                >
                  <FileText size={15} />
                </span>
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-sm font-medium">
                    {p.title}
                  </span>
                  <span className="mt-0.5 block truncate font-mono text-[11px] text-text-muted">
                    {p.id}@{p.version}
                  </span>
                  <span className="mt-2 flex flex-wrap gap-1.5">
                    <Pill>{p.scope}</Pill>
                    <Pill>{p.lang}</Pill>
                    <Pill>{t("rulesCount", { count: p.rule_count })}</Pill>
                    {p.active ? (
                      <Pill tone="success">{t("active")}</Pill>
                    ) : (
                      <Pill tone="muted">{t("draft")}</Pill>
                    )}
                  </span>
                </span>
              </div>
            </button>
          );
        })}
        {!isLoading && filtered.length === 0 && (
          <div className="p-4">
            <EmptyState
              icon={Search}
              title={t("noResultsTitle")}
              description={t("noResultsDesc")}
            />
          </div>
        )}
      </div>
    </aside>
  );
}
