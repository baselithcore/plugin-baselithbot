import { useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { AnimatePresence, motion } from 'motion/react';
import { Brain } from 'lucide-react';
import { useAuth } from '@auth';
import { ProtectedRoute } from '@auth/login';
import { useBrain } from './store';
import { pageVariants } from './lib/motion';
import { Aurora } from './components/Aurora';
import { Sidebar } from './components/Sidebar';
import { Topbar } from './components/Topbar';
import { RightRail } from './components/RightRail';
import { StatusBar } from './components/StatusBar';
import { CommandPalette } from './components/CommandPalette';
import { GraphPanel } from './components/GraphPanel';
import { AssistantPanel } from './components/AssistantPanel';
import { ConfirmHost } from './components/ConfirmDialog';
import { HistoryDrawer } from './components/HistoryDrawer';
import { TemplatesDialog } from './components/TemplatesDialog';
import { TrashView } from './components/TrashView';
import { Editor } from './editor/Editor';

/** Dashboard tab id — must match plugin.get_ui_tabs()[].id. */
const TAB_ID = 'baselithbrain';

function Dashboard() {
  const { canAccessTab } = useAuth();
  const init = useBrain((s) => s.init);
  const active = useBrain((s) => s.active);
  const reloadToken = useBrain((s) => s.reloadToken);
  const focusMode = useBrain((s) => s.focusMode);
  const modal = useBrain((s) => s.modal);
  const setModal = useBrain((s) => s.setModal);
  const setPalette = useBrain((s) => s.setPalette);
  const toggleGraph = useBrain((s) => s.toggleGraph);
  const toggleAssistant = useBrain((s) => s.toggleAssistant);
  const applyServerNote = useBrain((s) => s.applyServerNote);

  useEffect(() => {
    void init();
  }, [init]);

  // Global shortcuts: ⌘/Ctrl+K palette, ⌘/Ctrl+G graph, ⌘/Ctrl+J assistant.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const mod = e.metaKey || e.ctrlKey;
      if (mod && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        setPalette(true);
      } else if (mod && e.key.toLowerCase() === 'g') {
        e.preventDefault();
        toggleGraph();
      } else if (mod && e.key.toLowerCase() === 'j') {
        e.preventDefault();
        toggleAssistant();
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [setPalette, toggleGraph, toggleAssistant]);

  // Surface gate (default-allow): canAccessTab returns true when the policy is
  // unknown/unrestricted, so this only hides the dashboard when an admin has
  // explicitly restricted this plugin's tab and denied the current user.
  if (!canAccessTab(TAB_ID, 'baselithbrain')) {
    return <AccessDenied />;
  }

  return (
    <div className="relative flex h-full w-full overflow-hidden">
      <Aurora />
      <div className="relative z-10 flex h-full w-full gap-2.5 p-2.5">
        {!focusMode && <Sidebar />}
        <main className="bb-glass relative flex min-w-0 flex-1 flex-col overflow-hidden rounded-[var(--radius-lg)]">
          <Topbar />
          <div className="flex-1 overflow-y-auto py-10">
            <AnimatePresence mode="wait">
              {active ? (
                <motion.div
                  key={`${active.id}:${reloadToken}`}
                  variants={pageVariants}
                  initial="hidden"
                  animate="show"
                  exit="exit"
                >
                  <Editor noteId={active.id} body={active.body} onSaved={applyServerNote} />
                </motion.div>
              ) : (
                <Empty key="empty" />
              )}
            </AnimatePresence>
          </div>
          <StatusBar />
        </main>
        {!focusMode && <RightRail />}
      </div>
      <CommandPalette />
      <GraphPanel />
      <AssistantPanel />
      <HistoryDrawer open={modal === 'history'} onClose={() => setModal(null)} />
      <TemplatesDialog open={modal === 'templates'} onClose={() => setModal(null)} />
      <TrashView open={modal === 'trash'} onClose={() => setModal(null)} />
      <ConfirmHost />
    </div>
  );
}

/**
 * App root with the shared central-auth login wall. ProtectedRoute (inside the
 * AuthProvider from main.tsx) renders the spinner during SSO refresh and the
 * shared LoginPage when unauthenticated; otherwise it renders the dashboard.
 */
export default function App() {
  return (
    <ProtectedRoute>
      <Dashboard />
    </ProtectedRoute>
  );
}

function AccessDenied() {
  const { t } = useTranslation();
  return (
    <div className="relative flex h-full w-full items-center justify-center overflow-hidden">
      <Aurora />
      <div className="relative z-10 flex flex-col items-center gap-3 text-center">
        <div className="bb-glass flex size-14 items-center justify-center rounded-2xl text-[var(--color-muted)]">
          <Brain className="size-7" />
        </div>
        <h2 className="text-xl font-semibold tracking-tight">{t('app.accessDeniedTitle')}</h2>
        <p className="max-w-sm text-sm text-[var(--color-muted)]">{t('app.accessDeniedBody')}</p>
      </div>
    </div>
  );
}

function Empty() {
  const { t } = useTranslation();
  const createNote = useBrain((s) => s.createNote);
  return (
    <motion.div
      variants={pageVariants}
      initial="hidden"
      animate="show"
      exit="exit"
      className="flex h-[60vh] flex-col items-center justify-center gap-4 text-center"
    >
      <motion.div
        initial={{ opacity: 0, y: 4 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.16, ease: [0.22, 1, 0.36, 1] }}
        className="bb-glass flex size-14 items-center justify-center rounded-xl text-[var(--color-accent)]"
      >
        <Brain className="size-7" />
      </motion.div>
      <div>
        <h2 className="text-xl font-semibold tracking-tight">{t('app.emptyTitle')}</h2>
        <p className="mt-1 text-sm text-[var(--color-muted)]">{t('app.emptyBody')}</p>
      </div>
      <button
        onClick={() => void createNote()}
        className="bb-gradient bb-btn-glow rounded-lg px-4 py-2 text-sm font-medium text-white"
      >
        {t('app.emptyCta')}
      </button>
    </motion.div>
  );
}
