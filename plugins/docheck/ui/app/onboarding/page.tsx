"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import {
  Shield,
  Cpu,
  ListChecks,
  KeyRound,
  CheckCircle2,
  ArrowRight,
  ArrowLeft,
  type LucideIcon,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/cn";

const STEP_DEFS = [
  { id: "welcome", icon: Shield },
  { id: "model", icon: Cpu },
  { id: "policies", icon: ListChecks },
  { id: "keys", icon: KeyRound },
  { id: "done", icon: CheckCircle2 },
] as const;

export default function OnboardingPage() {
  const t = useTranslations("onboarding");
  const router = useRouter();
  const [step, setStep] = useState(0);
  const stepTitle = (id: (typeof STEP_DEFS)[number]["id"]) => {
    switch (id) {
      case "welcome":
        return t("steps.welcome");
      case "model":
        return t("steps.model");
      case "policies":
        return t("steps.policies");
      case "keys":
        return t("steps.keys");
      case "done":
        return t("steps.done");
    }
  };
  const STEPS = STEP_DEFS.map((s) => ({ ...s, title: stepTitle(s.id) }));
  const current = STEPS[step];
  const Icon: LucideIcon = current.icon;

  function next() {
    if (step < STEPS.length - 1) setStep(step + 1);
    else {
      localStorage.setItem("docheck.onboarded", "1");
      router.push("/");
    }
  }

  return (
    <div className="min-h-screen relative overflow-hidden bg-bg-canvas flex items-center justify-center p-6">
      <div className="relative w-full max-w-2xl rounded-lg border border-border surface-elev shadow-panel overflow-hidden">
        <header className="px-6 py-5 border-b border-border">
          <div className="flex items-center justify-between gap-4 mb-4">
            <div className="text-[10px] font-semibold uppercase tracking-[0.2em] text-text-muted">
              {t("header", { step: step + 1, total: STEPS.length })}
            </div>
            <button
              onClick={() => router.push("/")}
              className="text-[11px] text-text-muted hover:text-text-primary transition-colors"
            >
              {t("skip")}
            </button>
          </div>
          <div className="flex items-center gap-2">
            {STEPS.map((s, i) => (
              <div key={s.id} className="flex flex-1 items-center gap-2">
                <div
                  className={cn(
                    "flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-[10px] font-semibold transition-colors",
                    i < step &&
                      "bg-status-success/20 text-status-success border border-status-success/30",
                    i === step && "bg-status-info text-white",
                    i > step &&
                      "bg-bg-panel-elev text-text-muted border border-border",
                  )}
                >
                  {i < step ? <CheckCircle2 size={13} /> : i + 1}
                </div>
                {i < STEPS.length - 1 && (
                  <span
                    className={cn(
                      "h-px flex-1",
                      i < step ? "bg-status-success/40" : "bg-border",
                    )}
                  />
                )}
              </div>
            ))}
          </div>
        </header>

        <div className="px-6 py-8 min-h-[280px] animate-fade-in">
          <div className="flex h-10 w-10 items-center justify-center rounded-md border border-status-info/40 bg-status-info/10 text-status-info">
            <Icon className="w-5 h-5" />
          </div>
          <h1 className="mt-5 text-xl font-semibold tracking-tight">
            {current.title}
          </h1>

          <div className="mt-3 text-sm text-text-secondary leading-6 space-y-3">
            {current.id === "welcome" && <p>{t("welcomeText")}</p>}
            {current.id === "model" && (
              <>
                <p>
                  {t("modelPrimary")} <Mono>llama-3.3-70b-instruct-q4km</Mono>
                </p>
                <p>
                  {t("modelFallback")} <Mono>llama-3.1-8b-instruct</Mono>
                </p>
                <p className="text-xs text-text-muted">{t("modelNote")}</p>
              </>
            )}
            {current.id === "policies" && (
              <>
                <p>{t("policiesIntro")}</p>
                <ul className="space-y-1.5 text-xs">
                  <Bullet>{t("policiesGdpr")}</Bullet>
                  <Bullet>{t("policiesCivile")}</Bullet>
                  <Bullet>{t("policiesAi")}</Bullet>
                </ul>
                <p className="text-xs text-text-muted pt-1">
                  {t("policiesEditable")}
                </p>
              </>
            )}
            {current.id === "keys" && (
              <>
                <p>{t("keysIntro")}</p>
                <p className="text-xs text-text-muted">
                  {t("keysStored")} <Mono>~/.docheck/audit_ed25519.key</Mono>{" "}
                  {t("keysStoredSuffix")}
                </p>
                <div className="mt-3 rounded-md border border-status-warning/30 bg-status-warning/10 p-3 text-xs text-status-warning">
                  {t("keysWarning")}
                </div>
              </>
            )}
            {current.id === "done" && (
              <>
                <p>{t("doneIntro")}</p>
                <pre className="mt-1 rounded-md border border-border bg-bg-canvas p-3 font-mono text-xs text-text-secondary">
                  uv run python scripts/seed_admin.py
                </pre>
              </>
            )}
          </div>
        </div>

        <footer className="px-6 py-4 border-t border-border flex justify-between bg-bg-panel/50">
          <Button
            variant="ghost"
            size="sm"
            disabled={step === 0}
            onClick={() => setStep(Math.max(0, step - 1))}
          >
            <ArrowLeft size={13} /> {t("back")}
          </Button>
          <Button variant="primary" size="sm" onClick={next}>
            {step === STEPS.length - 1 ? t("finish") : t("next")}{" "}
            <ArrowRight size={13} />
          </Button>
        </footer>
      </div>
    </div>
  );
}

function Mono({ children }: { children: React.ReactNode }) {
  return (
    <code className="font-mono text-[12px] text-text-secondary">
      {children}
    </code>
  );
}

function Bullet({ children }: { children: React.ReactNode }) {
  return (
    <li className="flex items-start gap-2 text-text-secondary">
      <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-status-info" />
      <span>{children}</span>
    </li>
  );
}
