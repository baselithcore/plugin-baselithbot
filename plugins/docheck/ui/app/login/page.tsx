"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import {
  Database,
  LockKeyhole,
  LogIn,
  Network,
  Shield,
  type LucideIcon,
} from "lucide-react";
import { login } from "@/lib/auth";
import { Button } from "@/components/ui/button";

export default function LoginPage() {
  const t = useTranslations("login");
  const tCommon = useTranslations("common");
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await login(email, password);
      router.push("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : t("errorFailed"));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen relative overflow-hidden bg-bg-canvas">
      <div className="relative mx-auto grid min-h-screen max-w-6xl items-center px-4 py-8 lg:grid-cols-[1fr_440px] lg:gap-10">
        <section className="hidden flex-col justify-between gap-10 p-8 lg:flex">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-md border border-border-strong bg-bg-panel-elev flex items-center justify-center">
              <Shield className="w-5 h-5 text-status-info" />
            </div>
            <div>
              <div className="text-base font-semibold tracking-tight">
                {tCommon("appName")}
              </div>
              <div className="text-[10px] uppercase tracking-[0.2em] text-text-muted">
                {tCommon("tagline")}
              </div>
            </div>
          </div>

          <div>
            <div className="inline-flex items-center gap-2 rounded-md border border-status-info/30 bg-status-info/10 px-3 py-1 text-[11px] font-medium text-status-info">
              <span className="h-1.5 w-1.5 rounded-full bg-status-info animate-pulse-soft" />
              {t("badge")}
            </div>
            <h1 className="mt-6 max-w-xl text-[34px] leading-[1.1] font-semibold tracking-tight text-text-primary">
              {t("headline")}
            </h1>
            <p className="mt-5 max-w-xl text-sm leading-6 text-text-secondary">
              {t("subtitle")}
            </p>
          </div>

          <div className="grid grid-cols-3 gap-3">
            <Trait
              icon={LockKeyhole}
              title={t("traits.egressTitle")}
              text={t("traits.egressText")}
            />
            <Trait
              icon={Database}
              title={t("traits.auditTitle")}
              text={t("traits.auditText")}
            />
            <Trait
              icon={Network}
              title={t("traits.agentsTitle")}
              text={t("traits.agentsText")}
            />
          </div>
        </section>

        <div className="flex items-center justify-center">
          <div className="w-full max-w-sm rounded-lg border border-border surface-elev p-7 shadow-panel">
            <div className="mb-7 lg:hidden">
              <div className="flex items-center gap-2">
                <Shield className="w-6 h-6 text-status-info" />
                <h1 className="text-lg font-semibold">{tCommon("appName")}</h1>
              </div>
            </div>
            <div className="mb-6">
              <h2 className="text-xl font-semibold tracking-tight">
                {t("title")}
              </h2>
              <p className="mt-1.5 text-sm text-text-muted">{t("subtitle2")}</p>
            </div>

            <form onSubmit={onSubmit} className="space-y-4">
              <Field label={t("email")}>
                <input
                  type="email"
                  autoComplete="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full h-10 px-3 bg-bg-canvas border border-border rounded-md text-sm outline-none focus:border-status-info/60 focus:ring-2 focus:ring-status-info/20 transition-colors"
                />
              </Field>

              <Field label={t("password")}>
                <input
                  type="password"
                  autoComplete="current-password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full h-10 px-3 bg-bg-canvas border border-border rounded-md text-sm outline-none focus:border-status-info/60 focus:ring-2 focus:ring-status-info/20 transition-colors"
                />
              </Field>

              {error && (
                <p
                  className="rounded-md border border-status-danger/30 bg-status-danger/10 px-3 py-2 text-xs text-status-danger"
                  role="alert"
                >
                  {error}
                </p>
              )}

              <Button
                type="submit"
                variant="primary"
                size="lg"
                disabled={loading}
                className="w-full"
              >
                <LogIn size={16} />
                {loading ? t("signingIn") : t("signIn")}
              </Button>
            </form>

            <div className="mt-6 flex items-center justify-center gap-2 text-[11px] text-text-muted">
              <LockKeyhole size={11} className="text-status-success" />
              {t("footer")}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function Field({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <label className="block">
      <span className="text-[11px] uppercase tracking-wide text-text-muted mb-1.5 block">
        {label}
      </span>
      {children}
    </label>
  );
}

function Trait({
  icon: Icon,
  title,
  text,
}: {
  icon: LucideIcon;
  title: string;
  text: string;
}) {
  return (
    <div className="rounded-lg border border-border bg-bg-panel p-4 transition-colors hover:border-border-strong">
      <Icon size={16} className="text-status-info" />
      <div className="mt-3 text-sm font-semibold">{title}</div>
      <div className="mt-1 text-[11px] text-text-muted">{text}</div>
    </div>
  );
}
