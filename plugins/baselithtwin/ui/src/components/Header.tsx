// Top bar: identity, gateway connection state, autonomy mode, and the language
// switcher. The connection dot reflects the live SSE channel, not a poll.

import { useTranslation } from 'react-i18next';
import { Bot, Wifi, WifiOff, LogOut, Pause, Play } from 'lucide-react';
import { useAuth } from '@auth';
import type { TwinStatus } from '../api/types';
import { Badge, Button } from './ui';
import { LanguageSwitcher } from './LanguageSwitcher';

export function Header({
  status,
  connected,
  onTogglePause,
}: {
  status: TwinStatus | null;
  connected: boolean;
  onTogglePause?: (paused: boolean) => void;
}) {
  const { t } = useTranslation();
  const { user, logout, hasRole } = useAuth();
  const autonomy = status ? t(`autonomy.${status.autonomy}`) : '—';
  const paused = status?.paused ?? false;
  // Only an admin may operate the kill-switch (matches the backend guard).
  const canControl = typeof hasRole === 'function' ? hasRole('admin') : false;
  return (
    <header className="flex flex-wrap items-center justify-between gap-4">
      <div className="flex items-center gap-3">
        <div className="grid h-11 w-11 place-items-center rounded-2xl bg-gradient-to-br from-brand-500 to-accent-500 shadow-lg shadow-brand-500/30">
          <Bot className="h-6 w-6 text-ink-900" aria-hidden />
        </div>
        <div>
          <h1 className="text-lg font-semibold text-white">
            {status?.owner_name ?? '—'} <span className="text-white/40">· {t('app.title')}</span>
          </h1>
          <p className="text-xs text-white/40">{t('app.subtitle')}</p>
        </div>
      </div>
      <div className="flex items-center gap-2">
        <Badge tone="brand">
          {t('header.autonomy')}: {autonomy}
        </Badge>
        <Badge tone={connected ? 'good' : 'bad'}>
          {connected ? (
            <Wifi className="h-3 w-3" aria-hidden />
          ) : (
            <WifiOff className="h-3 w-3" aria-hidden />
          )}
          {connected ? t('header.connected') : t('header.disconnected')}
        </Badge>
        {paused && <Badge tone="warn">{t('header.paused')}</Badge>}
        {canControl && onTogglePause && (
          <Button
            variant={paused ? 'primary' : 'danger'}
            onClick={() => onTogglePause(!paused)}
            title={paused ? t('control.resume') : t('control.pause')}
          >
            {paused ? (
              <Play className="h-3.5 w-3.5" aria-hidden />
            ) : (
              <Pause className="h-3.5 w-3.5" aria-hidden />
            )}
            {paused ? t('control.resume') : t('control.pause')}
          </Button>
        )}
        <LanguageSwitcher />
        {user && (
          <>
            <Badge tone="neutral">{user.username || user.email}</Badge>
            <Button variant="ghost" onClick={() => logout()} title={t('auth.logout')}>
              <LogOut className="h-3.5 w-3.5" aria-hidden />
              {t('auth.logout')}
            </Button>
          </>
        )}
      </div>
    </header>
  );
}
