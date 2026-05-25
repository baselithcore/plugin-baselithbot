"use client";

import { useTranslations } from "next-intl";
import { Languages } from "lucide-react";
import { useLocaleStore } from "@/lib/i18n/store";
import { LOCALES, type Locale } from "@/lib/i18n/config";
import { cn } from "@/lib/cn";

const FLAG: Record<Locale, string> = { it: "IT", en: "EN", fr: "FR" };

export function LocaleSwitcher() {
  const t = useTranslations("topbar");
  const locale = useLocaleStore((s) => s.locale);
  const setLocale = useLocaleStore((s) => s.setLocale);

  return (
    <div
      role="group"
      aria-label={t("language")}
      className="hidden md:inline-flex h-8 items-center rounded-md border border-border bg-bg-canvas overflow-hidden"
    >
      <span className="px-2 text-text-muted" aria-hidden>
        <Languages size={13} />
      </span>
      {LOCALES.map((l) => (
        <button
          key={l}
          type="button"
          onClick={() => setLocale(l)}
          aria-pressed={locale === l}
          className={cn(
            "px-2 h-full text-[11px] font-mono tracking-wide transition-colors",
            locale === l
              ? "bg-bg-panel-elev text-text-primary"
              : "text-text-muted hover:text-text-primary",
          )}
        >
          {FLAG[l]}
        </button>
      ))}
    </div>
  );
}
