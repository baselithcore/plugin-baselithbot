"use client";

import {
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  User as UserIcon,
} from "lucide-react";
import { useTranslations } from "next-intl";
import { cn } from "@/lib/cn";

export type T = ReturnType<typeof useTranslations>;

export function Avatar({ tone }: { tone: "user" | "assistant" }) {
  if (tone === "user") {
    return (
      <div className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full border border-border bg-bg-canvas text-text-secondary">
        <UserIcon size={13} />
      </div>
    );
  }
  return (
    <div className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full border border-status-info/30 bg-status-info/10 text-status-info">
      <Sparkles size={13} />
    </div>
  );
}

export function GroundedBadge({ grounded, t }: { grounded: boolean; t: T }) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full border px-1.5 py-0.5 text-[9px] font-medium normal-case tracking-normal",
        grounded
          ? "border-status-success/40 bg-status-success/10 text-status-success"
          : "border-status-warning/40 bg-status-warning/10 text-status-warning",
      )}
      title={grounded ? t("groundedHint") : t("notGroundedHint")}
    >
      {grounded ? <ShieldCheck size={9} /> : <ShieldAlert size={9} />}
      {grounded ? t("groundedLabel") : t("notGroundedShort")}
    </span>
  );
}

export function IconBtn({
  children,
  onClick,
  label,
  disabled,
}: {
  children: React.ReactNode;
  onClick: () => void;
  label: string;
  disabled?: boolean;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      title={label}
      aria-label={label}
      disabled={disabled}
      className="inline-flex h-6 w-6 items-center justify-center rounded-md text-text-muted hover:bg-bg-panel-elev hover:text-text-primary transition-colors ring-focus disabled:opacity-50 disabled:cursor-not-allowed"
    >
      {children}
    </button>
  );
}

export function Banner({
  tone,
  icon: Icon,
  children,
}: {
  tone: "warning" | "danger";
  icon: typeof ShieldAlert;
  children: React.ReactNode;
}) {
  const cls =
    tone === "danger"
      ? "border-status-danger/30 bg-status-danger/10 text-status-danger"
      : "border-status-warning/30 bg-status-warning/10 text-status-warning";
  return (
    <div
      className={cn(
        "flex items-start gap-2 rounded-md border px-3 py-2 text-[12px] leading-5",
        cls,
      )}
    >
      <Icon size={13} className="mt-0.5 shrink-0" />
      <span>{children}</span>
    </div>
  );
}

function Dot({ delay }: { delay: string }) {
  return (
    <span
      className="h-1.5 w-1.5 rounded-full bg-status-info animate-bounce"
      style={{ animationDelay: delay, animationDuration: "1s" }}
    />
  );
}

export function ThinkingIndicator({ t }: { t: T }) {
  return (
    <div className="flex items-start gap-2.5" aria-live="polite">
      <Avatar tone="assistant" />
      <div className="flex-1">
        <div className="mb-1 text-[10px] uppercase tracking-wide text-text-muted">
          {t("assistantLabel")}
        </div>
        <div className="inline-flex items-center gap-2 rounded-lg border border-border bg-bg-canvas px-3 py-2.5">
          <span className="flex gap-1">
            <Dot delay="0ms" />
            <Dot delay="150ms" />
            <Dot delay="300ms" />
          </span>
          <span className="text-[12px] text-text-muted">{t("thinking")}</span>
        </div>
      </div>
    </div>
  );
}
