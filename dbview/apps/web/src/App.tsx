import { Suspense, lazy, useEffect, useRef } from 'react';
import {
  Panel,
  PanelGroup,
  PanelResizeHandle,
  type ImperativePanelHandle,
} from 'react-resizable-panels';
import { Toaster } from 'sonner';
import { motion } from 'framer-motion';
import { useQuery } from '@tanstack/react-query';
import { ChevronLeft, ChevronRight, Database, Sparkles } from 'lucide-react';
import { TopBar } from './components/TopBar.js';
import { StatusBar } from './components/StatusBar.js';
import { ConnectionPanel } from './components/ConnectionPanel.js';
import { GraphViewport } from './components/GraphViewport.js';
import { NL2QueryPanel } from './components/NL2QueryPanel.js';
import { DetailDrawer } from './components/DetailDrawer.js';
import { TourProvider } from './components/tour/TourProvider.js';
import { api } from './lib/api.js';
import { useAppStore } from './store/app.js';

// Deferred overlays — none of these are visible on first paint, so loading
// them on demand keeps the initial bundle smaller and the first interaction
// snappier. Each is mounted only when its open flag flips to true; closing
// unmounts immediately so we never keep heavy editor / table machinery in
// the tree while the user is back on the canvas.
const CommandPalette = lazy(() =>
  import('./components/CommandPalette.js').then((m) => ({ default: m.CommandPalette }))
);
const SettingsDialog = lazy(() =>
  import('./components/SettingsDialog.js').then((m) => ({ default: m.SettingsDialog }))
);
const UsersDialog = lazy(() =>
  import('./components/UsersDialog.js').then((m) => ({ default: m.UsersDialog }))
);
const HistoryPanel = lazy(() =>
  import('./components/HistoryPanel.js').then((m) => ({ default: m.HistoryPanel }))
);

function ResizeHandle({ hidden = false }: { hidden?: boolean }) {
  return (
    <PanelResizeHandle
      className="group relative w-2 transition-colors"
      aria-label="Resize panel"
      disabled={hidden}
    >
      {!hidden && (
        <span className="absolute inset-y-6 left-1/2 w-px -translate-x-1/2 rounded-full bg-border-subtle transition-all group-hover:w-1 group-hover:bg-accent/45 group-data-[resize-handle-state=drag]:w-1 group-data-[resize-handle-state=drag]:bg-accent" />
      )}
    </PanelResizeHandle>
  );
}

interface RailProps {
  side: 'left' | 'right';
  label: string;
  shortcut: string;
  icon: React.ReactNode;
  onExpand: () => void;
}

function CollapsedRail({ side, label, shortcut, icon, onExpand }: RailProps) {
  const isLeft = side === 'left';
  return (
    <button
      onClick={onExpand}
      title={`${label} (${shortcut})`}
      aria-label={`Expand ${label}`}
      className="group flex flex-col items-center justify-between h-full w-10 shrink-0 rounded-lg border py-3 transition-colors hover:bg-surface-2/70"
      style={{
        borderColor: 'rgb(var(--border-subtle))',
        background: 'rgb(var(--surface-elevated) / 0.68)',
      }}
    >
      <span className="flex flex-col items-center gap-2 text-text-muted group-hover:text-text">
        {isLeft ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
        {icon}
      </span>
      <span
        className="text-[10px] font-medium tracking-wide uppercase text-text-dim group-hover:text-text-muted"
        style={{ writingMode: 'vertical-rl', transform: isLeft ? 'rotate(180deg)' : undefined }}
      >
        {label}
      </span>
      <span />
    </button>
  );
}

export function App() {
  const theme = useAppStore((s) => s.theme);
  const connId = useAppStore((s) => s.activeConnectionId);
  const leftCollapsed = useAppStore((s) => s.leftCollapsed);
  const rightCollapsed = useAppStore((s) => s.rightCollapsed);
  const setLeftCollapsed = useAppStore((s) => s.setLeftCollapsed);
  const setRightCollapsed = useAppStore((s) => s.setRightCollapsed);
  const toggleLeft = useAppStore((s) => s.toggleLeftCollapsed);
  const toggleRight = useAppStore((s) => s.toggleRightCollapsed);
  const commandOpen = useAppStore((s) => s.commandOpen);
  const setCommandOpen = useAppStore((s) => s.setCommandOpen);
  const settingsOpen = useAppStore((s) => s.settingsOpen);
  const usersOpen = useAppStore((s) => s.usersOpen);
  const historyOpen = useAppStore((s) => s.historyOpen);

  const leftRef = useRef<ImperativePanelHandle>(null);
  const rightRef = useRef<ImperativePanelHandle>(null);

  const schema = useQuery({
    queryKey: ['schema', connId],
    queryFn: () => api.getSchema(connId!),
    enabled: !!connId,
  });

  // Min sizes mirror the Panel minSize props below. When the user re-opens a
  // collapsed sidebar we want it to come back at the smallest legible width
  // so the central canvas keeps the focus — they can drag the handle wider
  // afterwards if they want.
  const LEFT_MIN_SIZE = 17;
  const RIGHT_MIN_SIZE = 22;

  // Sync persisted flags → imperative panel state on mount and when toggled
  // by something other than dragging (header buttons, keyboard shortcuts).
  useEffect(() => {
    const p = leftRef.current;
    if (!p) return;
    if (leftCollapsed && !p.isCollapsed()) p.collapse();
    if (!leftCollapsed && p.isCollapsed()) {
      p.expand();
      // expand() restores the previously-saved size; clamp to min so re-opening
      // never reclaims a wide layout from a forgotten earlier session.
      requestAnimationFrame(() => p.resize(LEFT_MIN_SIZE));
    }
  }, [leftCollapsed]);

  useEffect(() => {
    const p = rightRef.current;
    if (!p) return;
    if (rightCollapsed && !p.isCollapsed()) p.collapse();
    if (!rightCollapsed && p.isCollapsed()) {
      p.expand();
      requestAnimationFrame(() => p.resize(RIGHT_MIN_SIZE));
    }
  }, [rightCollapsed]);

  // Keyboard shortcuts: ⌘/Ctrl + [ left, ⌘/Ctrl + ] right, ⌘/Ctrl + K palette.
  // ⌘K lives here (not inside CommandPalette) so the palette stays a lazy
  // chunk: the shortcut must work even before the palette has been mounted.
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (!(e.metaKey || e.ctrlKey)) return;
      if (e.key.toLowerCase() === 'k') {
        e.preventDefault();
        setCommandOpen(!useAppStore.getState().commandOpen);
        return;
      }
      const tag = (e.target as HTMLElement | null)?.tagName;
      if (tag === 'INPUT' || tag === 'TEXTAREA') return;
      if (e.key === '[') {
        e.preventDefault();
        toggleLeft();
      } else if (e.key === ']') {
        e.preventDefault();
        toggleRight();
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [toggleLeft, toggleRight, setCommandOpen]);

  return (
    <div className="app-shell h-screen w-screen flex flex-col text-text antialiased">
      <TopBar />
      <motion.main
        initial={{ opacity: 0, y: 6 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.32, ease: [0.22, 1, 0.36, 1], delay: 0.08 }}
        className="flex-1 min-h-0 p-2 md:p-3 flex gap-2"
      >
        {leftCollapsed && (
          <CollapsedRail
            side="left"
            label="Connections"
            shortcut="⌘["
            icon={<Database className="w-4 h-4" />}
            onExpand={() => setLeftCollapsed(false)}
          />
        )}
        <PanelGroup
          direction="horizontal"
          className="h-full gap-2 flex-1"
          autoSaveId="dbview-layout"
        >
          <Panel
            ref={leftRef}
            defaultSize={21}
            minSize={17}
            maxSize={32}
            collapsible
            collapsedSize={0}
            onCollapse={() => setLeftCollapsed(true)}
            onExpand={() => setLeftCollapsed(false)}
            className="min-h-0"
          >
            <ConnectionPanel />
          </Panel>
          <ResizeHandle hidden={leftCollapsed} />
          <Panel defaultSize={51} minSize={34} className="min-h-0">
            <GraphViewport />
          </Panel>
          <ResizeHandle hidden={rightCollapsed} />
          <Panel
            ref={rightRef}
            defaultSize={28}
            minSize={22}
            maxSize={48}
            collapsible
            collapsedSize={0}
            onCollapse={() => setRightCollapsed(true)}
            onExpand={() => setRightCollapsed(false)}
            className="min-h-0"
          >
            <NL2QueryPanel />
          </Panel>
        </PanelGroup>
        {rightCollapsed && (
          <CollapsedRail
            side="right"
            label="Query assistant"
            shortcut="⌘]"
            icon={<Sparkles className="w-4 h-4" />}
            onExpand={() => setRightCollapsed(false)}
          />
        )}
      </motion.main>
      <StatusBar />
      <DetailDrawer schema={schema.data} />
      <Suspense fallback={null}>
        {commandOpen && <CommandPalette />}
        {settingsOpen && <SettingsDialog />}
        {usersOpen && <UsersDialog />}
        {historyOpen && <HistoryPanel />}
      </Suspense>
      <TourProvider />
      <Toaster
        theme={theme}
        position="top-right"
        richColors
        closeButton
        toastOptions={{
          style: {
            background: 'rgb(var(--surface-1))',
            border: '1px solid rgb(var(--border))',
            color: 'rgb(var(--text))',
          },
        }}
      />
    </div>
  );
}
