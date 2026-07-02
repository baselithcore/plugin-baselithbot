import { AnimatePresence, MotionConfig } from 'motion/react';
import { useStatusStream } from '@/hooks/useStatusStream';
import { useMe } from '@/hooks/useMe';
import { useAccess } from '@/hooks/useAccess';
import { useCostUsage } from '@/hooks/useCostUsage';
import { useControlStore } from '@/store/useControlStore';
import { Shell } from '@/components/Shell';
import { Toaster } from '@/components/Toaster';
import { ConfirmDialog } from '@/components/ConfirmDialog';
import { ErrorBoundary } from '@/components/ErrorBoundary';
import { Overview } from '@/pages/Overview';
import { PluginDetail } from '@/pages/PluginDetail';
import { EventFeed } from '@/pages/EventFeed';
import { Logs } from '@/pages/Logs';
import { SystemConsole } from '@/pages/SystemConsole';
import { Account } from '@/pages/Account';

export default function App() {
  useStatusStream();
  useMe();
  useAccess();
  useCostUsage();
  const selected = useControlStore((s) => s.selected);
  const select = useControlStore((s) => s.select);
  const currentTab = useControlStore((s) => s.currentTab);
  const me = useControlStore((s) => s.me);

  return (
    // reducedMotion="user" honors the OS "reduce motion" setting (accessibility).
    <MotionConfig reducedMotion="user">
      <Shell>
        {/* A crash in one page must not blank the whole dashboard; navigating
            (resetKey change) re-arms the boundary automatically. */}
        <ErrorBoundary resetKey={`${currentTab}:${selected ?? ''}`}>
          <AnimatePresence mode="wait">
            {selected ? (
              <PluginDetail key={selected} name={selected} onBack={() => select(null)} />
            ) : currentTab === 'events' ? (
              <EventFeed key="events" />
            ) : currentTab === 'logs' ? (
              <Logs key="logs" />
            ) : currentTab === 'system' ? (
              <SystemConsole key="system" />
            ) : currentTab === 'account' && me ? (
              <Account key="account" me={me} />
            ) : (
              <Overview key="overview" onOpen={(name) => select(name)} />
            )}
          </AnimatePresence>
        </ErrorBoundary>
      </Shell>
      <Toaster />
      <ConfirmDialog />
    </MotionConfig>
  );
}
