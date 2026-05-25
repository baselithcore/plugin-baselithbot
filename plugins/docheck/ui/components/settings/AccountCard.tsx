"use client";

import { KeyRound, LogOut } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";
import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { logout, type AuthSession } from "@/lib/auth";
import { ChangePasswordDialog } from "./ChangePasswordDialog";
import { CopyValue, Mono, Row, Section, StatusPill } from "./SettingsShared";

export function AccountCard({
  session,
  tenant,
}: {
  session: AuthSession | null;
  tenant: string;
}) {
  const t = useTranslations("settings.account");
  const router = useRouter();
  const [pwOpen, setPwOpen] = useState(false);
  const [logoutOpen, setLogoutOpen] = useState(false);

  function doLogout() {
    logout();
    toast.success(t("signedOut"));
    router.replace("/login");
  }

  return (
    <Section
      title={t("title")}
      icon={KeyRound}
      actions={
        <>
          <Button size="sm" variant="secondary" onClick={() => setPwOpen(true)}>
            {t("changePassword")}
          </Button>
          <Button
            size="sm"
            variant="ghost"
            onClick={() => setLogoutOpen(true)}
            aria-label={t("signOut")}
          >
            <LogOut size={13} />
            {t("signOut")}
          </Button>
        </>
      }
    >
      <Row label={t("email")}>{session?.email ?? "—"}</Row>
      <Row label={t("roles")}>
        <span className="inline-flex flex-wrap justify-end gap-1.5">
          {session?.roles.length
            ? session.roles.map((r) => (
                <StatusPill key={r} tone="info">
                  {r}
                </StatusPill>
              ))
            : "—"}
        </span>
      </Row>
      <Row label={t("userId")}>
        {session?.user_id ? (
          <CopyValue value={session.user_id} />
        ) : (
          <Mono>—</Mono>
        )}
      </Row>
      <Row label={t("tenant")}>
        <Mono>{tenant}</Mono>
      </Row>

      <ChangePasswordDialog open={pwOpen} onOpenChange={setPwOpen} />
      <ConfirmDialog
        open={logoutOpen}
        onOpenChange={setLogoutOpen}
        title={t("logoutTitle")}
        description={t("logoutDescription")}
        confirmLabel={t("signOut")}
        onConfirm={doLogout}
      />
    </Section>
  );
}
