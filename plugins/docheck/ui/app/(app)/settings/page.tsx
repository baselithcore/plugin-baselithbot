'use client';

import { useQuery } from '@tanstack/react-query';
import { CheckCircle2, Loader2, Settings as SettingsIcon, XCircle } from 'lucide-react';
import { useEffect, useState } from 'react';
import { useTranslations } from 'next-intl';
import { TopBar } from '@/components/TopBar';
import { PageHeader } from '@/components/PageHeader';
import { Button } from '@/components/ui/button';
import { AccountCard } from '@/components/settings/AccountCard';
import { CacheCard } from '@/components/settings/CacheCard';
import { EngineCard } from '@/components/settings/EngineCard';
import { SecurityCard } from '@/components/settings/SecurityCard';
import { StorageCard } from '@/components/settings/StorageCard';
import { getHealth } from '@/lib/api';
import { getRuntimeInfo } from '@/lib/api/system';
import { getSession, getTenant, type AuthSession } from '@/lib/auth';

export default function SettingsPage() {
  const t = useTranslations('settings');
  const [session, setSession] = useState<AuthSession | null>(null);
  const [tenant, setTenant] = useState<string>('default');

  useEffect(() => {
    setSession(getSession());
    setTenant(getTenant());
  }, []);

  const isAdmin = !!session?.roles.includes('admin');

  const runtime = useQuery({
    queryKey: ['system', 'runtime'],
    queryFn: getRuntimeInfo,
  });
  const health = useQuery({
    queryKey: ['system', 'health'],
    queryFn: getHealth,
    refetchInterval: 15_000,
  });

  return (
    <div className="h-screen flex flex-col">
      <TopBar />
      <main className="flex-1 overflow-auto p-6">
        <div className="mx-auto max-w-5xl">
          <PageHeader
            eyebrow={t('eyebrow')}
            eyebrowIcon={SettingsIcon}
            title={t('title')}
            description={t('description')}
            actions={
              <Button
                size="sm"
                variant="ghost"
                onClick={() => {
                  runtime.refetch();
                  health.refetch();
                }}
                disabled={runtime.isFetching || health.isFetching}
              >
                {runtime.isFetching || health.isFetching ? (
                  <Loader2 size={13} className="animate-spin" />
                ) : null}
                {t('reload')}
              </Button>
            }
          />

          <div className="grid gap-5 lg:grid-cols-2">
            <AccountCard session={session} tenant={tenant} />
            <EngineCard />
            <SecurityCard runtime={runtime.data} />
            <StorageCard runtime={runtime.data} isAdmin={isAdmin} />
            <CacheCard isAdmin={isAdmin} />
          </div>

          <div className="mt-6 flex flex-col items-center gap-1.5 text-[11px] text-text-muted">
            <span className="inline-flex items-center gap-2">
              {health.data ? (
                <>
                  <CheckCircle2 size={13} className="text-status-success" />
                  {t('engineHealthy', { version: health.data.version })}
                </>
              ) : health.isError ? (
                <>
                  <XCircle size={13} className="text-status-danger" />
                  {t('engineUnreachable')}
                </>
              ) : (
                <>
                  <Loader2 size={13} className="animate-spin" />
                  {t('contacting')}
                </>
              )}
            </span>
            <span>
              {runtime.data
                ? `${runtime.data.app_name} · ${runtime.data.debug ? t('buildDebug') : t('buildProduction')}`
                : t('fallbackBuildLine')}
            </span>
          </div>
        </div>
      </main>
    </div>
  );
}
