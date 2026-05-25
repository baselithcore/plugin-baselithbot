"use client";

import * as Dialog from "@radix-ui/react-dialog";
import { Loader2, Lock } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";
import { changePassword } from "@/lib/api/system";

interface Props {
  open: boolean;
  onOpenChange: (v: boolean) => void;
}

export function ChangePasswordDialog({ open, onOpenChange }: Props) {
  const t = useTranslations("settings.password");
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [busy, setBusy] = useState(false);

  function reset() {
    setCurrent("");
    setNext("");
    setConfirm("");
    setBusy(false);
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (next.length < 8) return toast.error(t("errMinLen"));
    if (next !== confirm) return toast.error(t("errMismatch"));
    if (next === current) return toast.error(t("errSame"));

    setBusy(true);
    try {
      await changePassword(current, next);
      toast.success(t("toastUpdated"));
      reset();
      onOpenChange(false);
    } catch (e) {
      toast.error((e as Error).message);
      setBusy(false);
    }
  }

  return (
    <Dialog.Root
      open={open}
      onOpenChange={(v) => {
        if (!v) reset();
        onOpenChange(v);
      }}
    >
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-40 bg-bg-canvas/60 backdrop-blur-[2px] animate-fade-in" />
        <Dialog.Content
          className="fixed left-1/2 top-1/2 z-50 w-[min(440px,92vw)] surface-elev rounded-xl border border-border p-5 shadow-popover animate-dialog-in"
          style={{ transform: "translate(-50%, -50%)" }}
        >
          <div className="flex items-start gap-3">
            <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md border border-border bg-bg-canvas text-status-info">
              <Lock size={16} />
            </span>
            <div className="min-w-0">
              <Dialog.Title className="text-sm font-semibold">
                {t("title")}
              </Dialog.Title>
              <Dialog.Description className="mt-1.5 text-xs leading-5 text-text-muted">
                {t("description")}
              </Dialog.Description>
            </div>
          </div>
          <form onSubmit={submit} className="mt-4 space-y-3">
            <Field label={t("current")}>
              <input
                type="password"
                autoComplete="current-password"
                required
                value={current}
                onChange={(e) => setCurrent(e.target.value)}
                className="w-full h-9 px-3 bg-bg-canvas border border-border rounded-md text-sm outline-none focus:border-status-info/60 focus:ring-2 focus:ring-status-info/20 transition-colors"
              />
            </Field>
            <Field label={t("new")}>
              <input
                type="password"
                autoComplete="new-password"
                required
                minLength={8}
                value={next}
                onChange={(e) => setNext(e.target.value)}
                className="w-full h-9 px-3 bg-bg-canvas border border-border rounded-md text-sm outline-none focus:border-status-info/60 focus:ring-2 focus:ring-status-info/20 transition-colors"
              />
            </Field>
            <Field label={t("confirm")}>
              <input
                type="password"
                autoComplete="new-password"
                required
                minLength={8}
                value={confirm}
                onChange={(e) => setConfirm(e.target.value)}
                className="w-full h-9 px-3 bg-bg-canvas border border-border rounded-md text-sm outline-none focus:border-status-info/60 focus:ring-2 focus:ring-status-info/20 transition-colors"
              />
            </Field>
            <div className="mt-5 flex justify-end gap-2">
              <Button
                type="button"
                size="sm"
                variant="ghost"
                onClick={() => onOpenChange(false)}
                disabled={busy}
              >
                {t("cancel")}
              </Button>
              <Button type="submit" size="sm" variant="primary" disabled={busy}>
                {busy && <Loader2 size={13} className="animate-spin" />}
                {t("update")}
              </Button>
            </div>
          </form>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
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
      <span className="block text-[11px] font-medium uppercase tracking-wide text-text-muted">
        {label}
      </span>
      <span className="mt-1.5 block">{children}</span>
    </label>
  );
}
