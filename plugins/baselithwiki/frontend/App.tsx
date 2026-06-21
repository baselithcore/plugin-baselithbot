import { useEffect, useMemo, useRef, useState } from 'react';
import { AppHeader } from './components/AppHeader';
import { AppToaster } from './components/AppToaster';
import { CommandPalette } from './components/CommandPalette';
import { Composer } from './components/Composer';
import { EmptyState } from './components/EmptyState';
import { PendingSynthHint } from './components/PendingSynthHint';
import { WhatsNewModal } from './components/WhatsNewModal';
import { HelpModal } from './components/HelpModal';
import { MemoriesModal } from './components/MemoriesModal';
import { MessageList } from './components/MessageList';
import {
  readSettings,
  saveSettings,
  SettingsModal,
  type Settings,
} from './components/SettingsModal';
import { SetupWizard } from './components/SetupWizard';
import { Sidebar } from './components/Sidebar';
import { SourcesDrawer } from './components/Sources';
import { UploadModal } from './components/UploadModal';
import { AdminShell } from './components/admin/AdminShell';
import { AdminEmbedsPage } from './components/admin/AdminEmbedsPage';
import { AdminFeedbackPage } from './components/admin/AdminFeedbackPage';
import { GraphPage } from './pages/GraphPage';
import { useLocation, navigate } from './hooks/useLocation';
import { useAuth } from './contexts/AuthContext';
import { useDomain } from './contexts/DomainContext';
import { useChat } from './hooks/useChat';
import { useConversations } from './hooks/useConversations';
import { useEditions } from './hooks/useEditions';
import { useFeatures } from './hooks/useFeatures';
import { useAppShortcuts } from './hooks/useAppShortcuts';
import type { Message } from './lib/types';
import { cn } from './lib/cn';
import { buildPaletteItems } from './lib/palette-items';

export function App() {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [sourcesOpen, setSourcesOpen] = useState(false);
  const [activeDocId, setActiveDocId] = useState<string | null>(null);
  const [activeAnchor, setActiveAnchor] = useState<string | null>(null);
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [helpOpen, setHelpOpen] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [uploadOpen, setUploadOpen] = useState(false);
  const [wizardOpen, setWizardOpen] = useState(false);
  const [memoriesOpen, setMemoriesOpen] = useState(false);
  const { path: locationPath } = useLocation();
  // Sticky flag: once the user submits the scaffold, keep the wizard
  // mounted through the DonePanel (restart + ingestion) phase. Without
  // this the next /branding refresh (triggered by `onScaffolded`) flips
  // setup_mode → false, App unmounts the wizard, and the user lands in
  // the main UI before seeing the docs ingest. Cleared by the wizard's
  // own `window.location.reload()` at the end.
  const [scaffoldInFlight, setScaffoldInFlight] = useState(false);
  const { branding, refresh: refreshBranding } = useDomain();
  const { user, ready: authReady, can } = useAuth();
  const setupRequired =
    scaffoldInFlight || (!!branding && (branding.setup_mode === true || branding.domain === ''));
  // Identity is owned by the central ``auth`` plugin: the SPA is wrapped by
  // ``@auth``'s ProtectedRoute (see main.tsx), so by the time App renders the
  // user is always authenticated. No local login/bootstrap gate remains.
  const [settings, setSettingsState] = useState<Settings>(() => readSettings());
  const setSettings = (s: Settings) => {
    setSettingsState(s);
    saveSettings(s);
  };
  // Knowledge graph expansion: sempre attivo. Il toggle nel composer
  // è stato rimosso — i collegamenti vengono usati di default per
  // ogni query (utile per domande comparative o trasversali).
  const useGraph = true;
  const features = useFeatures();
  const { editions, editionId, setEditionId, editionLabel } = useEditions();

  const handlePickSource = (docId: string, anchor?: string) => {
    setActiveDocId(docId);
    setActiveAnchor(anchor ?? null);
  };

  // Ref-based sync per rompere ciclo useChat ↔ useConversations:
  // useChat ha bisogno di `conversationId` al momento del `send()`, non
  // al momento dell'init hook. Usiamo ref aggiornati dagli effect dopo
  // che useConversations ha popolato `activeId` e `attachServerConversationId`.
  const conversationIdRef = useRef<string | null>(null);
  const attachServerConversationIdRef = useRef<((id: string) => void) | null>(null);

  const { messages, isStreaming, send, regenerate, editAndResend, stop, setMessages } = useChat({
    graph: useGraph,
    limit: settings.retrievalLimit,
    conversationIdRef,
    onConversationId: (id) => attachServerConversationIdRef.current?.(id),
  });

  const {
    conversations,
    activeId,
    active,
    setActiveId,
    newChat: handleNewChat,
    rename: handleRenameConv,
    togglePin: handleTogglePin,
    remove: handleDeleteConv,
    attachServerConversationId,
  } = useConversations({ messages, setMessages, isStreaming });

  // Tieni ref in sync con state corrente di useConversations.
  useEffect(() => {
    conversationIdRef.current = activeId;
  }, [activeId]);
  useEffect(() => {
    attachServerConversationIdRef.current = attachServerConversationId;
  }, [attachServerConversationId]);

  // Shortcuts gated by perm. Senza la perm associata il tasto è no-op:
  // niente surface open per features cui l'utente non ha accesso (coerente
  // con `<Can>` lato UI: hide affordance + ignora keybinding). Sidebar
  // toggle resta sempre attivo — è chrome layout, non feature.
  useAppShortcuts({
    onNewChat: () => {
      if (!can('conversation.write')) return;
      void handleNewChat();
    },
    onToggleSidebar: () => setSidebarOpen((v) => !v),
    onTogglePalette: () => {
      if (!can('view.command_palette')) return;
      setPaletteOpen((v) => !v);
    },
    onToggleSettings: () => {
      if (!can('view.settings')) return;
      setSettingsOpen((v) => !v);
    },
    onToggleUpload: () => {
      if (!can('ingest.run')) return;
      setUploadOpen((v) => !v);
    },
    onToggleWizard: () => {
      if (!can('admin.scaffold')) return;
      setWizardOpen((v) => !v);
    },
    onToggleHelp: () => {
      if (!can('view.help')) return;
      setHelpOpen((v) => !v);
    },
  });

  const handleSend = async (text: string) => {
    if (!activeId) {
      // newChat ritorna l'id appena creato (locale o server). Update
      // SINCRONO del ref prima di `send`: l'effect che sincronizza
      // `conversationIdRef.current = activeId` corre solo dopo il
      // commit React, quindi una await Promise.resolve() non basta —
      // useChat leggerebbe ref=null e la prima query da home andrebbe
      // persa (utente percepiva "primo click non invia, secondo sì").
      const newId = await handleNewChat();
      conversationIdRef.current = newId;
    }
    await send(text);
  };

  const paletteItems = useMemo(
    () =>
      buildPaletteItems({
        conversations,
        setSettings,
        setActiveId,
        setSidebarOpen,
        setSourcesOpen,
        openUpload: () => setUploadOpen(true),
        openWizard: () => setWizardOpen(true),
        openSettings: () => setSettingsOpen(true),
        openHelp: () => setHelpOpen(true),
        newChat: () => void handleNewChat(),
      }),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [conversations]
  );

  const allSources = useMemo(() => {
    const seen = new Map<string, Message['sources'] extends (infer U)[] | undefined ? U : never>();
    for (const m of messages) {
      for (const s of m.sources ?? []) {
        if (!seen.has(s.document_id)) seen.set(s.document_id, s);
      }
    }
    return Array.from(seen.values());
  }, [messages]);

  // Branding still loading OR auth bootstrap in corso: blank canvas
  // (evita flash di UI stale chat o di AuthPage prima che il refresh
  // cookie abbia ripristinato la sessione persistita).
  if (!branding || !authReady) {
    return <div className="h-screen w-screen bg-canvas" aria-hidden="true" />;
  }

  // Setup wizard: utente loggato (o auth disabilitato) ma nessun pack
  // attivo. Wizard occupa il viewport finché APP_DOMAIN non è scelto.
  if (setupRequired) {
    return (
      <>
        <SetupWizard
          open
          blocking
          variant="screen"
          onClose={() => {
            /* blocking — no-op */
          }}
          onScaffolded={() => {
            setScaffoldInFlight(true);
            refreshBranding();
          }}
        />
        <AppToaster />
      </>
    );
  }

  // Graph route — full-page knowledge-graph viz (graphify PR3). Gating:
  // auth required, then `graph.read` (mig 013). Backend applica lo stesso
  // gate via dependency sul router `/api/graph/*`; il check qui evita un
  // round-trip 403 per utenti senza permesso e li redirige a `/`.
  if (locationPath.startsWith('/graph')) {
    if (!can('graph.read')) {
      navigate('/');
      return null;
    }
    return <GraphPage />;
  }

  // Admin routes — wiki-specific surfaces only (embeds + feedback). Users,
  // roles and groups are owned by the central ``auth`` plugin's Access Control,
  // so the wiki no longer exposes them. Gating uses the central-derived perms;
  // an effective admin (``user.role === 'admin'``) passes everything.
  const adminRoute = locationPath.startsWith('/admin/embeds')
    ? 'embeds'
    : locationPath.startsWith('/admin/feedback')
      ? 'feedback'
      : null;
  if (adminRoute) {
    const perms = user?.permissions ?? [];
    const requiredPerm = adminRoute === 'embeds' ? 'admin.embed.manage' : 'feedback.read';
    const canManage = user?.role === 'admin' || perms.includes(requiredPerm);
    if (!canManage) {
      navigate('/', true);
      return null;
    }
    return (
      <>
        <AdminShell active={adminRoute}>
          {adminRoute === 'embeds' ? <AdminEmbedsPage /> : <AdminFeedbackPage />}
        </AdminShell>
        <AppToaster />
      </>
    );
  }

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-canvas text-ink">
      <Sidebar
        open={sidebarOpen}
        onToggle={() => setSidebarOpen((v) => !v)}
        conversations={conversations}
        activeId={activeId}
        onSelect={setActiveId}
        onNewChat={() => void handleNewChat()}
        canNewChat={can('conversation.write')}
        onDelete={can('conversation.delete') ? (id) => void handleDeleteConv(id) : undefined}
        onRename={can('conversation.write') ? (id, t) => void handleRenameConv(id, t) : undefined}
        onTogglePin={can('conversation.write') ? (id) => void handleTogglePin(id) : undefined}
      />

      <a href="#main-content" className="skip-link">
        Vai al contenuto
      </a>

      <main id="main-content" className={cn('flex flex-1 flex-col min-w-0 relative bg-canvas')}>
        <AppHeader
          active={active}
          messageUserCount={messages.filter((m) => m.role === 'user').length}
          onOpenPalette={() => setPaletteOpen(true)}
          onOpenUpload={() => setUploadOpen(true)}
          onOpenWizard={() => setWizardOpen(true)}
          onOpenSettings={() => setSettingsOpen(true)}
          onOpenHelp={() => setHelpOpen(true)}
          onOpenMemories={() => setMemoriesOpen(true)}
          editions={editions}
          editionId={editionId}
          setEditionId={setEditionId}
          allSourcesCount={allSources.length}
          sourcesOpen={sourcesOpen}
          onOpenSources={() => setSourcesOpen(true)}
        />

        <WhatsNewModal />
        <PendingSynthHint />

        {messages.length === 0 ? (
          <EmptyState onPick={handleSend} />
        ) : (
          <MessageList
            messages={messages}
            onPickSource={handlePickSource}
            onOpenSources={() => setSourcesOpen(true)}
            editionLabel={editionLabel}
            onRegenerate={regenerate}
            onEdit={editAndResend}
            isStreaming={isStreaming}
            showTrace={settings.showTrace}
            showTimer={settings.showTimer}
            feedbackEnabled={features.feedback_enabled}
          />
        )}

        <Composer onSend={handleSend} onStop={stop} isStreaming={isStreaming} />
      </main>

      <SourcesDrawer
        open={sourcesOpen}
        onClose={() => setSourcesOpen(false)}
        sources={allSources}
        activeDocId={activeDocId}
        activeAnchor={activeAnchor}
        onSelect={(id, anchor) => {
          setActiveDocId(id);
          setActiveAnchor(anchor ?? null);
        }}
      />

      <CommandPalette
        open={paletteOpen}
        onClose={() => setPaletteOpen(false)}
        items={paletteItems}
      />
      <HelpModal open={helpOpen} onClose={() => setHelpOpen(false)} />
      <SettingsModal
        open={settingsOpen}
        onClose={() => setSettingsOpen(false)}
        settings={settings}
        onChange={setSettings}
      />
      <UploadModal open={uploadOpen} onClose={() => setUploadOpen(false)} />
      <MemoriesModal open={memoriesOpen} onClose={() => setMemoriesOpen(false)} />
      <SetupWizard
        open={wizardOpen}
        onClose={() => setWizardOpen(false)}
        onScaffolded={() => {
          // refresh branding so first-run gate clears once user restarts
          refreshBranding();
        }}
      />

      <AppToaster />
    </div>
  );
}
