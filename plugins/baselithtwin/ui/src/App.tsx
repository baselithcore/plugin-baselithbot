// Dashboard shell: composes the panels over the data hook and the live SSE feed.
// Relevant stream events trigger targeted re-fetches so the UI stays in sync
// with the twin without aggressive polling.

import { useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { AuthProvider, useAuth } from '@auth';
import { ProtectedRoute } from '@auth/login';
import { useTwin } from './hooks/useTwin';
import { useStream } from './hooks/useStream';
import type { StreamEvent } from './api/types';
import { Header } from './components/Header';
import { StatCards } from './components/StatCards';
import { LiveFeed } from './components/LiveFeed';
import { ApprovalQueue } from './components/ApprovalQueue';
import { StylePanel } from './components/StylePanel';
import { WhitelistPanel } from './components/WhitelistPanel';
import { MemoryPanel } from './components/MemoryPanel';
import { AuditPanel } from './components/AuditPanel';

// Matches the plugin's UI tab id (BaselithTwinPlugin.metadata.name).
const TAB_ID = 'baselithtwin';

const REFRESHING_EVENTS = new Set([
  'queued',
  'auto_sent',
  'decided',
  'inbound',
  'style_trained',
  'control',
]);

export default function App() {
  return (
    <AuthProvider>
      <ProtectedRoute>
        <Dashboard />
      </ProtectedRoute>
    </AuthProvider>
  );
}

function AccessDenied() {
  const { t } = useTranslation();
  return (
    <div className="grid min-h-screen place-items-center bg-ink-900 px-4 text-center text-white">
      <div className="max-w-sm space-y-2">
        <h1 className="text-xl font-semibold">{t('auth.denied.title')}</h1>
        <p className="text-sm text-white/50">{t('auth.denied.body')}</p>
      </div>
    </div>
  );
}

function Dashboard() {
  const { t } = useTranslation();
  const { canAccessTab } = useAuth();
  const twin = useTwin();

  const onEvent = useCallback(
    (e: StreamEvent) => {
      if (REFRESHING_EVENTS.has(e.type)) {
        void twin.refreshStatus();
        void twin.refreshQueue();
        void twin.refreshAudit();
      }
    },
    [twin]
  );
  const { events, connected } = useStream(onEvent);

  // Default-allow RBAC gate (true when unknown/unrestricted), no login wall.
  if (!canAccessTab(TAB_ID, 'baselithtwin')) {
    return <AccessDenied />;
  }

  return (
    <div className="min-h-screen bg-ink-900 bg-[radial-gradient(60rem_40rem_at_70%_-10%,rgba(34,211,238,0.08),transparent),radial-gradient(50rem_30rem_at_-10%_20%,rgba(139,92,246,0.08),transparent)] px-4 py-6 text-white sm:px-8">
      <div className="mx-auto max-w-7xl space-y-6">
        <Header status={twin.status} connected={connected} onTogglePause={twin.setPaused} />
        {twin.error && (
          <div className="rounded-xl border border-rose-500/20 bg-rose-500/10 px-4 py-2 text-sm text-rose-300">
            {t('common.error')} — {twin.error}
          </div>
        )}
        <StatCards status={twin.status} />

        <div className="grid gap-6 lg:grid-cols-3">
          <div className="space-y-6 lg:col-span-2">
            <ApprovalQueue queue={twin.queue} onDecide={twin.decide} />
            <WhitelistPanel
              entries={twin.whitelist}
              onAdd={twin.addWhitelist}
              onRemove={twin.removeWhitelist}
            />
            <MemoryPanel facts={twin.facts} />
          </div>
          <div className="space-y-6">
            <LiveFeed events={events} />
            <StylePanel style={twin.style} onTrain={twin.trainStyle} />
            <AuditPanel events={twin.audit} />
          </div>
        </div>
      </div>
    </div>
  );
}
