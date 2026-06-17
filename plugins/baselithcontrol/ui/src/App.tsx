import { AnimatePresence, MotionConfig } from 'motion/react';
import { useStatusStream } from '@/hooks/useStatusStream';
import { useMe } from '@/hooks/useMe';
import { useAccess } from '@/hooks/useAccess';
import { useControlStore } from '@/store/useControlStore';
import { Shell } from '@/components/Shell';
import { Toaster } from '@/components/Toaster';
import { ConfirmDialog } from '@/components/ConfirmDialog';
import { Overview } from '@/pages/Overview';
import { PluginDetail } from '@/pages/PluginDetail';
import { EventFeed } from '@/pages/EventFeed';
import { SystemConsole } from '@/pages/SystemConsole';

export default function App() {
  useStatusStream();
  useMe();
  useAccess();
  const selected = useControlStore((s) => s.selected);
  const select = useControlStore((s) => s.select);
  const currentTab = useControlStore((s) => s.currentTab);

  return (
    // reducedMotion="user" honors the OS "reduce motion" setting (accessibility).
    <MotionConfig reducedMotion="user">
      <Shell>
        <AnimatePresence mode="wait">
          {selected ? (
            <PluginDetail key={selected} name={selected} onBack={() => select(null)} />
          ) : currentTab === 'events' ? (
            <EventFeed key="events" />
          ) : currentTab === 'system' ? (
            <SystemConsole key="system" />
          ) : (
            <Overview key="overview" onOpen={(name) => select(name)} />
          )}
        </AnimatePresence>
      </Shell>
      <Toaster />
      <ConfirmDialog />
    </MotionConfig>
  );
}
