"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import {
  ChevronDown,
  Command,
  LogOut,
  Search,
  Settings as SettingsIcon,
  SlidersHorizontal,
  User as UserIcon,
} from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { LocaleSwitcher } from "@/components/i18n/LocaleSwitcher";
import { getSession, logout, getTenant, type AuthSession } from "@/lib/auth";
import { getHealth } from "@/lib/api";
import { useAppStore } from "@/lib/store";
import { notify } from "@/lib/notifications";
import { PolicyManager } from "@/components/policy/PolicyManager";
import { NotificationsBell } from "@/components/NotificationsBell";
import { ThemeToggle } from "@/components/ThemeToggle";
import { Button } from "./ui/button";
import { StatusDot } from "./ui/status-dot";
import { Kbd } from "./ui/kbd";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "./ui/tooltip";
import { cn } from "@/lib/cn";

export function TopBar() {
  const router = useRouter();
  const t = useTranslations("topbar");
  const tCommon = useTranslations("common");
  const [session, setSession] = useState<AuthSession | null>(null);
  const [tenant, setTenantState] = useState<string>("default");
  const [menu, setMenu] = useState(false);
  const [policyOpen, setPolicyOpen] = useState(false);
  const [searchOpen, setSearchOpen] = useState(false);
  const selectedPolicies = useAppStore((s) => s.selectedPolicies);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setSession(getSession());
    setTenantState(getTenant());
  }, []);

  useEffect(() => {
    function onClick(e: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(e.target as Node))
        setMenu(false);
    }
    function onKey(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setSearchOpen((v) => !v);
      }
      if (e.key === "Escape") setSearchOpen(false);
    }
    document.addEventListener("mousedown", onClick);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onClick);
      document.removeEventListener("keydown", onKey);
    };
  }, []);

  function onLogout() {
    logout();
    router.replace("/login");
  }

  return (
    <TooltipProvider delayDuration={150}>
      <header className="h-14 border-b border-border bg-bg-panel flex items-center justify-between px-4 lg:px-6 sticky top-0 z-30">
        <div className="flex min-w-0 items-center gap-3">
          <div className="flex flex-col leading-tight">
            <div className="flex items-center gap-2 text-[10px] uppercase tracking-[0.2em] text-text-muted">
              <span className="h-px w-4 bg-border" />
              {tCommon("appName")}
            </div>
            <div className="text-sm font-semibold text-text-primary tracking-tight">
              {t("subtitle")}
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2 lg:gap-2.5">
          <button
            type="button"
            onClick={() => setSearchOpen(true)}
            className="hidden xl:flex h-9 w-[320px] items-center gap-2 rounded-md border border-border bg-bg-canvas px-3 text-xs text-text-muted hover:border-border-strong hover:bg-bg-panel transition-colors ring-focus"
          >
            <Search size={14} />
            <span className="flex-1 text-left">{t("searchPlaceholder")}</span>
            <Kbd>⌘</Kbd>
            <Kbd>K</Kbd>
          </button>

          <ModelStatus />

          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="secondary"
                size="sm"
                onClick={() => setPolicyOpen(true)}
                className="gap-2"
              >
                <SlidersHorizontal size={13} />
                <span className="hidden sm:inline">{t("policies")}</span>
                <span className="rounded border border-status-info/30 bg-status-info/10 px-1.5 py-0.5 text-[10px] font-mono text-status-info">
                  {selectedPolicies.length}
                </span>
              </Button>
            </TooltipTrigger>
            <TooltipContent side="bottom">
              {t("policiesTooltip")}
            </TooltipContent>
          </Tooltip>

          <LocaleSwitcher />

          <ThemeToggle />

          <NotificationsBell />

          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="outline"
                size="icon-sm"
                aria-label={t("settings")}
                onClick={() => router.push("/settings")}
              >
                <SettingsIcon className="w-4 h-4" />
              </Button>
            </TooltipTrigger>
            <TooltipContent side="bottom">{t("settings")}</TooltipContent>
          </Tooltip>

          <div className="relative" ref={menuRef}>
            <button
              type="button"
              onClick={() => setMenu((v) => !v)}
              aria-label={t("userMenu")}
              aria-expanded={menu}
              className={cn(
                "inline-flex items-center gap-2 px-2 h-8 rounded-md border border-border bg-bg-canvas hover:bg-bg-panel-elev transition-colors ring-focus",
                menu && "bg-bg-panel-elev border-border-strong",
              )}
            >
              <span className="flex h-5 w-5 items-center justify-center rounded border border-border-strong bg-bg-panel-elev text-[10px] font-semibold text-text-primary">
                {(session?.email ?? "?").slice(0, 1).toUpperCase()}
              </span>
              <span className="hidden md:inline max-w-[160px] truncate text-xs text-text-secondary">
                {session?.email ?? "..."}
              </span>
              <ChevronDown
                size={13}
                className={cn(
                  "text-text-muted transition-transform",
                  menu && "rotate-180",
                )}
              />
            </button>
            {menu && (
              <div className="absolute right-0 top-10 w-72 surface-elev border border-border rounded-lg shadow-popover p-2 z-40 animate-slide-up">
                <div className="px-3 py-2.5 border-b border-border/50">
                  <div className="flex items-center gap-2.5">
                    <span className="flex h-8 w-8 items-center justify-center rounded-md border border-border-strong bg-bg-panel-elev text-xs font-semibold text-text-primary">
                      {(session?.email ?? "?").slice(0, 1).toUpperCase()}
                    </span>
                    <div className="min-w-0 flex-1">
                      <div className="text-sm font-medium truncate">
                        {session?.email}
                      </div>
                      <div className="text-[10px] text-text-muted mt-0.5 font-mono">
                        {session?.roles.join(" / ") || tCommon("noRoles")}
                      </div>
                    </div>
                  </div>
                  <div className="mt-2.5 flex items-center justify-between text-[10px] text-text-muted">
                    <span>{tCommon("tenant")}</span>
                    <span className="font-mono text-text-secondary">
                      {tenant}
                    </span>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => router.push("/settings")}
                  className="w-full inline-flex items-center gap-2 px-3 h-9 text-sm text-text-secondary rounded-md hover:bg-bg-panel hover:text-text-primary transition-colors"
                >
                  <UserIcon size={14} /> {t("account")}
                </button>
                <button
                  type="button"
                  onClick={onLogout}
                  className="w-full inline-flex items-center gap-2 px-3 h-9 text-sm text-text-secondary rounded-md hover:bg-bg-panel hover:text-status-danger transition-colors"
                >
                  <LogOut size={14} /> {t("logout")}
                </button>
              </div>
            )}
          </div>
        </div>
        <PolicyManager open={policyOpen} onClose={() => setPolicyOpen(false)} />
        {searchOpen && <SearchDialog onClose={() => setSearchOpen(false)} />}
      </header>
    </TooltipProvider>
  );
}

function ModelStatus() {
  const t = useTranslations("topbar");
  const [last, setLast] = useState(Date.now());
  const health = useQuery({
    queryKey: ["health"],
    queryFn: getHealth,
    refetchInterval: 15_000,
  });
  useEffect(() => {
    const id = setInterval(() => setLast(Date.now()), 8000);
    return () => clearInterval(id);
  }, []);
  const ok = health.data?.status === "ok";
  const prevOk = useRef<boolean | null>(null);
  useEffect(() => {
    if (health.data === undefined) return;
    if (prevOk.current === null) {
      prevOk.current = ok;
      return;
    }
    if (prevOk.current && !ok) {
      notify({
        tone: "danger",
        title: "Local LLM offline",
        body: `${health.data.llm_provider ?? "llm"} unreachable at ${
          health.data.llm_base_url ?? ""
        }`,
        source: "runtime",
      });
    } else if (!prevOk.current && ok) {
      notify({
        tone: "success",
        title: "Local LLM ready",
        body: `${health.data.llm_provider ?? "llm"} back online`,
        source: "runtime",
      });
    }
    prevOk.current = ok;
  }, [ok, health.data]);
  const provider = health.data?.llm_provider ?? "llm";
  const providerLabel = provider.charAt(0).toUpperCase() + provider.slice(1);
  const tone = ok ? "success" : "warning";
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <span
          className={cn(
            "hidden sm:inline-flex items-center gap-2 text-xs px-2.5 h-8 rounded-md border cursor-default",
            ok
              ? "border-status-success/30 bg-status-success/10 text-status-success"
              : "border-status-warning/30 bg-status-warning/10 text-status-warning",
          )}
        >
          <StatusDot tone={tone} pulse={ok} />
          <span className="font-medium">
            {ok
              ? t("modelReady", { provider: providerLabel })
              : t("modelOffline", { provider: providerLabel })}
          </span>
          <span className="text-[10px] font-mono opacity-80">
            {Math.max(0, Math.floor((Date.now() - last) / 1000))}s
          </span>
        </span>
      </TooltipTrigger>
      <TooltipContent side="bottom">
        <div className="text-[11px]">
          <div className="font-medium text-text-primary">
            {t("modelTooltipTitle")}
          </div>
          <div className="mt-0.5 text-text-muted">
            {health.data?.llm_model ?? "—"} · {health.data?.llm_base_url ?? ""}
          </div>
          <div className="mt-0.5 text-text-muted">
            {t("modelTooltipEgress")}
          </div>
        </div>
      </TooltipContent>
    </Tooltip>
  );
}

function SearchDialog({ onClose }: { onClose: () => void }) {
  const t = useTranslations("topbar");
  return (
    <div
      role="dialog"
      aria-modal
      onClick={onClose}
      className="fixed inset-0 z-50 flex items-start justify-center bg-bg-canvas/80 pt-[14vh] animate-fade-in"
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className="w-[640px] max-w-[92vw] surface-elev rounded-lg border border-border shadow-popover overflow-hidden animate-slide-up"
      >
        <div className="flex items-center gap-3 border-b border-border/50 px-5 h-14">
          <Command size={15} className="text-text-muted" />
          <input
            autoFocus
            placeholder={t("searchDialogPlaceholder")}
            className="flex-1 bg-transparent text-sm text-text-primary placeholder:text-text-muted outline-none"
          />
          <Kbd>ESC</Kbd>
        </div>
        <div className="p-2">
          <div className="px-2 pt-2 pb-1 text-[10px] font-semibold uppercase tracking-[0.18em] text-text-muted">
            {t("quickActions")}
          </div>
          <SearchItem label={t("quick.documents")} hint="/documents" />
          <SearchItem label={t("quick.policies")} hint="/policies" />
          <SearchItem label={t("quick.audit")} hint="/audit" />
          <SearchItem label={t("quick.settings")} hint="/settings" />
        </div>
      </div>
    </div>
  );
}

function SearchItem({ label, hint }: { label: string; hint: string }) {
  return (
    <button
      type="button"
      className="w-full flex items-center justify-between rounded-md px-2.5 h-9 text-sm text-text-secondary hover:bg-bg-panel hover:text-text-primary transition-colors"
    >
      <span>{label}</span>
      <span className="font-mono text-[11px] text-text-muted">{hint}</span>
    </button>
  );
}
