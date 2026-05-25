"use client";

import { useEffect, useRef, useState } from "react";
import { Monitor, Moon, Sun, Check } from "lucide-react";
import { useTheme, type Theme } from "@/lib/theme";
import { cn } from "@/lib/cn";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "./ui/tooltip";

const OPTIONS: { key: Theme; icon: typeof Sun; label: string }[] = [
  { key: "light", icon: Sun, label: "Light" },
  { key: "dark", icon: Moon, label: "Dark" },
  { key: "system", icon: Monitor, label: "System" },
];

export function ThemeToggle() {
  const { theme, resolvedTheme, setTheme } = useTheme();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function onClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node))
        setOpen(false);
    }
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, []);

  const ActiveIcon = resolvedTheme === "dark" ? Moon : Sun;

  return (
    <TooltipProvider delayDuration={150}>
      <div className="relative" ref={ref}>
        <Tooltip>
          <TooltipTrigger asChild>
            <button
              type="button"
              aria-label="Theme"
              aria-haspopup="menu"
              aria-expanded={open}
              onClick={() => setOpen((v) => !v)}
              className={cn(
                "inline-flex h-8 w-8 items-center justify-center rounded-md border border-border bg-bg-canvas text-text-secondary hover:bg-bg-panel-elev hover:text-text-primary transition-colors ring-focus",
                open &&
                  "bg-bg-panel-elev border-border-strong text-text-primary",
              )}
            >
              <ActiveIcon size={14} />
            </button>
          </TooltipTrigger>
          <TooltipContent side="bottom">Theme</TooltipContent>
        </Tooltip>

        {open && (
          <div
            role="menu"
            className="absolute right-0 top-10 w-44 surface-elev border border-border rounded-lg shadow-popover p-1 z-40 animate-slide-up"
          >
            {OPTIONS.map(({ key, icon: Icon, label }) => {
              const active = theme === key;
              return (
                <button
                  key={key}
                  role="menuitemradio"
                  aria-checked={active}
                  type="button"
                  onClick={() => {
                    setTheme(key);
                    setOpen(false);
                  }}
                  className={cn(
                    "w-full inline-flex items-center gap-2 px-2.5 h-8 text-sm rounded-md transition-colors",
                    active
                      ? "bg-bg-panel text-text-primary"
                      : "text-text-secondary hover:bg-bg-panel hover:text-text-primary",
                  )}
                >
                  <Icon size={14} className="text-text-muted" />
                  <span className="flex-1 text-left">{label}</span>
                  {active && <Check size={13} className="text-status-info" />}
                </button>
              );
            })}
          </div>
        )}
      </div>
    </TooltipProvider>
  );
}
