"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import {
  Bell,
  CheckCheck,
  CircleAlert,
  CircleCheck,
  Info,
  TriangleAlert,
  X,
} from "lucide-react";
import { useNotifications, type NotificationItem } from "@/lib/notifications";
import { Button } from "./ui/button";
import { Tooltip, TooltipContent, TooltipTrigger } from "./ui/tooltip";
import { cn } from "@/lib/cn";

const TONE_ICON = {
  info: Info,
  success: CircleCheck,
  warning: TriangleAlert,
  danger: CircleAlert,
} as const;

const TONE_CLASS = {
  info: "text-status-info",
  success: "text-status-success",
  warning: "text-status-warning",
  danger: "text-status-danger",
} as const;

function useRelTime() {
  const t = useTranslations("notifications.ago");
  return (ts: number): string => {
    const diff = Math.max(0, Date.now() - ts);
    const s = Math.floor(diff / 1000);
    if (s < 60) return t("seconds", { count: s });
    const m = Math.floor(s / 60);
    if (m < 60) return t("minutes", { count: m });
    const h = Math.floor(m / 60);
    if (h < 24) return t("hours", { count: h });
    const d = Math.floor(h / 24);
    return t("days", { count: d });
  };
}

export function NotificationsBell() {
  const t = useTranslations("notifications");
  const relTime = useRelTime();
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const items = useNotifications((s) => s.items);
  const markAllRead = useNotifications((s) => s.markAllRead);
  const markRead = useNotifications((s) => s.markRead);
  const remove = useNotifications((s) => s.remove);
  const clear = useNotifications((s) => s.clear);
  const ref = useRef<HTMLDivElement>(null);
  const [, force] = useState(0);

  const unread = items.reduce((acc, i) => acc + (i.read ? 0 : 1), 0);

  useEffect(() => {
    function onClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node))
        setOpen(false);
    }
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") setOpen(false);
    }
    document.addEventListener("mousedown", onClick);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onClick);
      document.removeEventListener("keydown", onKey);
    };
  }, []);

  // Refresh relative timestamps while open.
  useEffect(() => {
    if (!open) return;
    const id = setInterval(() => force((n) => n + 1), 30_000);
    return () => clearInterval(id);
  }, [open]);

  function handleOpen() {
    setOpen((v) => {
      const next = !v;
      if (next && unread > 0) {
        // Mark read shortly after open so user notices the badge dropping.
        setTimeout(() => markAllRead(), 600);
      }
      return next;
    });
  }

  function handleClick(item: NotificationItem) {
    markRead(item.id);
    if (item.href) {
      router.push(item.href);
      setOpen(false);
    }
  }

  return (
    <div className="relative" ref={ref}>
      <Tooltip>
        <TooltipTrigger asChild>
          <Button
            variant="outline"
            size="icon-sm"
            aria-label={t("title")}
            aria-expanded={open}
            onClick={handleOpen}
            className="relative"
          >
            <Bell className="w-4 h-4" />
            {unread > 0 && (
              <span
                aria-label={t("unread", { count: unread })}
                className="absolute -top-1 -right-1 min-w-[16px] h-4 px-1 inline-flex items-center justify-center rounded-full bg-status-danger text-[9px] font-semibold text-white border border-bg-panel"
              >
                {unread > 9 ? "9+" : unread}
              </span>
            )}
          </Button>
        </TooltipTrigger>
        <TooltipContent side="bottom">{t("title")}</TooltipContent>
      </Tooltip>

      {open && (
        <div
          role="dialog"
          aria-label={t("title")}
          className="absolute right-0 top-10 w-[360px] surface-elev border border-border rounded-lg shadow-popover z-40 animate-slide-up overflow-hidden"
        >
          <div className="flex items-center justify-between px-3 py-2.5 border-b border-border/50">
            <div className="flex items-center gap-2">
              <span className="text-sm font-semibold text-text-primary">
                {t("title")}
              </span>
              <span className="text-[10px] font-mono text-text-muted">
                {items.length}
              </span>
            </div>
            <div className="flex items-center gap-1">
              <button
                type="button"
                onClick={markAllRead}
                disabled={unread === 0}
                className="inline-flex items-center gap-1 px-2 h-7 text-[11px] text-text-secondary rounded hover:bg-bg-panel hover:text-text-primary transition-colors disabled:opacity-40 disabled:hover:bg-transparent"
              >
                <CheckCheck size={12} /> {t("markRead")}
              </button>
              <button
                type="button"
                onClick={clear}
                disabled={items.length === 0}
                className="inline-flex items-center gap-1 px-2 h-7 text-[11px] text-text-secondary rounded hover:bg-bg-panel hover:text-status-danger transition-colors disabled:opacity-40 disabled:hover:bg-transparent"
              >
                {t("clear")}
              </button>
            </div>
          </div>

          <div className="max-h-[420px] overflow-y-auto">
            {items.length === 0 ? (
              <div className="px-4 py-10 text-center">
                <Bell className="mx-auto mb-2 text-text-muted" size={20} />
                <div className="text-xs text-text-muted">{t("noneYet")}</div>
                <div className="text-[10px] text-text-muted mt-1">
                  {t("systemHint")}
                </div>
              </div>
            ) : (
              <ul className="divide-y divide-border/40">
                {items.map((item) => {
                  const Icon = TONE_ICON[item.tone];
                  return (
                    <li
                      key={item.id}
                      className={cn(
                        "group relative px-3 py-2.5 hover:bg-bg-panel transition-colors cursor-pointer",
                        !item.read && "bg-status-info/[0.04]",
                      )}
                      onClick={() => handleClick(item)}
                    >
                      <div className="flex items-start gap-2.5">
                        <Icon
                          size={14}
                          className={cn(
                            "mt-0.5 shrink-0",
                            TONE_CLASS[item.tone],
                          )}
                        />
                        <div className="min-w-0 flex-1">
                          <div className="flex items-center gap-2">
                            <span className="text-xs font-medium text-text-primary truncate">
                              {item.title}
                            </span>
                            {!item.read && (
                              <span className="h-1.5 w-1.5 rounded-full bg-status-info shrink-0" />
                            )}
                          </div>
                          {item.body && (
                            <p className="mt-0.5 text-[11px] text-text-secondary line-clamp-2">
                              {item.body}
                            </p>
                          )}
                          <div className="mt-1 flex items-center gap-2 text-[10px] text-text-muted font-mono">
                            <span>{relTime(item.ts)}</span>
                            {item.source && (
                              <>
                                <span>·</span>
                                <span>{item.source}</span>
                              </>
                            )}
                          </div>
                        </div>
                        <button
                          type="button"
                          aria-label={t("dismiss")}
                          onClick={(e) => {
                            e.stopPropagation();
                            remove(item.id);
                          }}
                          className="opacity-0 group-hover:opacity-100 text-text-muted hover:text-text-primary transition-opacity p-0.5 rounded"
                        >
                          <X size={12} />
                        </button>
                      </div>
                    </li>
                  );
                })}
              </ul>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
