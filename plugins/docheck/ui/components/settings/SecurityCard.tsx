'use client';

import { useMutation, useQuery } from '@tanstack/react-query';
import { Loader2, LockKeyhole, ShieldCheck, ShieldAlert } from 'lucide-react';
import { toast } from 'sonner';
import { useTranslations } from 'next-intl';
import { Button } from '@/components/ui/button';
import { verifyAuditChain, type ChainStatus } from '@/lib/api';
import type { RuntimeInfo } from '@/lib/api/system';
import { CopyValue, Row, Section, StatusPill } from './SettingsShared';

interface PubKeyResponse {
  algorithm: string;
  public_key: string;
}

const BASE = process.env.NEXT_PUBLIC_API_BASE ?? 'http://127.0.0.1:8765/api/v1';

async function fetchPubkey(): Promise<PubKeyResponse> {
  const res = await fetch(`${BASE}/info/pubkey`);
  if (!res.ok) throw new Error(`pubkey ${res.status}`);
  return res.json();
}

export function SecurityCard({ runtime }: { runtime?: RuntimeInfo }) {
  const t = useTranslations('settings.security');
  const pubkeyQ = useQuery({
    queryKey: ['info', 'pubkey'],
    queryFn: fetchPubkey,
  });
  const chainQ = useQuery<ChainStatus | null>({
    queryKey: ['audit', 'verify', 'settings'],
    queryFn: () => verifyAuditChain().catch(() => null),
  });

  const verifyMut = useMutation({
    mutationFn: verifyAuditChain,
    onSuccess: (s) => {
      chainQ.refetch();
      if (s.ok) {
        toast.success(t('toastVerified', { count: s.total_entries }));
      } else {
        toast.error(t('toastBroken', { seq: s.broken_seq ?? '?' }));
      }
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const chain = chainQ.data;

  return (
    <Section
      title={t('title')}
      icon={LockKeyhole}
      actions={
        <Button
          size="sm"
          variant="secondary"
          onClick={() => verifyMut.mutate()}
          disabled={verifyMut.isPending}
        >
          {verifyMut.isPending ? (
            <Loader2 size={13} className="animate-spin" />
          ) : chain?.ok ? (
            <ShieldCheck size={13} />
          ) : (
            <ShieldAlert size={13} />
          )}
          {t('verifyChain')}
        </Button>
      }
    >
      <Row label={t('algorithm')}>Ed25519</Row>
      <Row label={t('publicKey')}>
        {pubkeyQ.data ? (
          <CopyValue value={pubkeyQ.data.public_key} />
        ) : (
          <span className="text-text-muted text-[11px]">{t('loading')}</span>
        )}
      </Row>
      <Row label={t('masterKey')}>
        <StatusPill tone="success">{t('masterKeyValue')}</StatusPill>
      </Row>
      <Row label={t('egress')}>
        <StatusPill tone="success">
          <span className="h-1.5 w-1.5 rounded-full bg-status-success animate-pulse-soft" />
          {t('egressLocked')}
        </StatusPill>
      </Row>
      <Row label={t('dbEncryption')}>
        {runtime ? (
          <StatusPill tone={runtime.db_encryption_enabled ? 'success' : 'warning'}>
            {runtime.db_encryption_enabled ? t('sqlcipher') : t('plain')}
          </StatusPill>
        ) : (
          <span className="text-text-muted text-[11px]">…</span>
        )}
      </Row>
      <Row label={t('authProvider')}>
        {runtime ? (
          <StatusPill tone="info">
            {runtime.oidc_enabled ? t('oidcLocal') : t('localPassword')}
          </StatusPill>
        ) : (
          <span className="text-text-muted text-[11px]">…</span>
        )}
      </Row>
      <Row label={t('auditChain')}>
        {chain ? (
          <span className="inline-flex flex-wrap items-center justify-end gap-2">
            <StatusPill tone={chain.ok ? 'success' : 'danger'}>
              {chain.ok ? t('intact') : t('broken', { seq: chain.broken_seq ?? '?' })}
            </StatusPill>
            <span className="text-[11px] text-text-muted">
              {t('entries', { count: chain.total_entries })}
            </span>
          </span>
        ) : (
          <span className="text-text-muted text-[11px]">{t('unverified')}</span>
        )}
      </Row>
    </Section>
  );
}
