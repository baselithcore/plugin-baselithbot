"use client";

import { useTranslations } from "next-intl";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/cn";
import type { CoverageReport } from "@/lib/api/types";

/**
 * ADR-0014 visualization.
 *
 * Non-blocking banner shown after a policy ingest. Surfaces:
 * - extracted / detected counts and a coverage ratio badge (color-coded),
 * - first N detected obligations that did not surface as extracted rules
 *   ("gaps"), each with its verbatim excerpt — operator can use them as
 *   prompts for manual rule creation.
 *
 * Coverage is informational ("stima" in copy). Render guarded by parent.
 */
export function CoverageBanner({
  policyId,
  policyVersion,
  coverage,
  onDismiss,
}: {
  policyId: string;
  policyVersion: string;
  coverage: CoverageReport;
  onDismiss: () => void;
}) {
  const t = useTranslations("policies.coverage");
  const pct = Math.round(coverage.coverage_ratio * 100);
  const tone =
    coverage.coverage_ratio >= 0.8
      ? "ok"
      : coverage.coverage_ratio >= 0.4
        ? "warn"
        : "bad";

  const toneClass = {
    ok: "bg-emerald-500/15 text-emerald-700 dark:text-emerald-300 border-emerald-500/30",
    warn: "bg-amber-500/15 text-amber-700 dark:text-amber-300 border-amber-500/30",
    bad: "bg-red-500/15 text-red-700 dark:text-red-300 border-red-500/30",
  }[tone];

  const gaps = coverage.gaps.slice(0, 5);

  return (
    <Card className="mb-4">
      <CardHeader>
        <div className="flex items-center gap-3">
          <span
            className={cn(
              "inline-flex h-7 items-center rounded-md border px-2 text-xs font-semibold",
              toneClass,
            )}
            aria-label={t("ratioLabel", { pct })}
          >
            {pct}%
          </span>
          <div>
            <CardTitle>{t("title")}</CardTitle>
            <p className="mt-1 text-xs text-text-muted">
              {t("subtitle", {
                id: policyId,
                version: policyVersion,
                extracted: coverage.extracted_count,
                detected: coverage.detected_count,
              })}
            </p>
          </div>
        </div>
        <button
          type="button"
          onClick={onDismiss}
          className="text-xs text-text-muted hover:text-text-primary"
          aria-label={t("dismiss")}
        >
          {t("dismiss")}
        </button>
      </CardHeader>
      {gaps.length > 0 ? (
        <CardContent className="border-t border-border pt-3">
          <p className="mb-2 text-xs font-medium text-text-primary">
            {t("gapsHeader", {
              shown: gaps.length,
              total: coverage.gaps.length,
            })}
          </p>
          <ul className="space-y-2">
            {gaps.map((g, i) => (
              <li
                key={`${policyId}-${policyVersion}-gap-${i}`}
                className="rounded-md border border-border bg-bg-panel-elev p-2"
              >
                <div className="flex items-baseline justify-between gap-2">
                  <span className="text-xs font-semibold text-text-primary">
                    {g.label || t("unnamedGap")}
                  </span>
                  <span className="text-[10px] uppercase tracking-wide text-text-muted">
                    {g.severity_hint}
                  </span>
                </div>
                <p className="mt-1 text-xs text-text-muted leading-5 italic">
                  &ldquo;{g.excerpt}&rdquo;
                </p>
              </li>
            ))}
          </ul>
          <p className="mt-3 text-[11px] text-text-muted">{t("hint")}</p>
        </CardContent>
      ) : null}
    </Card>
  );
}
