import { useEffect, useMemo, useRef, useState } from 'react';
import { AuthPage } from './components/AuthPage';
import { AcceptInvite } from './components/AcceptInvite';
import { AppHeader } from './components/AppHeader';
import { AppToaster } from './components/AppToaster';
import { BootstrapGate } from './components/BootstrapGate';
import { ForcePasswordChange } from './components/ForcePasswordChange';
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
import { AdminUsersPage } from './components/admin/AdminUsersPage';
import { AdminEmbedsPage } from './components/admin/AdminEmbedsPage';
import { AdminFeedbackPage } from './components/admin/AdminFeedbackPage';
import { AdminGroupsPage } from './components/admin/AdminGroupsPage';
import { AdminRolesPage } from './components/admin/AdminRolesPage';
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
  // Bootstrap gate: parte True. Il BootstrapGate verifica /auth/bootstrap/status
  // e chiama onComplete (che setta False) sia se needs_bootstrap=false sia
  // dopo creazione superuser riuscita.
  const [bootstrapPending, setBootstrapPending] = useState(true);
  // Sticky flag: once the user submits the scaffold, keep the wizard
  // mounted through the DonePanel (restart + ingestion) phase. Without
  // this the next /branding refresh (triggered by `onScaffolded`) flips
  // setup_mode → false, App unmounts the wizard, and the user lands in
  // the main UI before seeing the docs ingest. Cleared by the wizard's
  // own `window.location.reload()` at the end.
  const [scaffoldInFlight, setScaffoldInFlight] = useState(false);
  const { branding, refresh: refreshBranding } = useDomain();
  const { user, ready: authReady, authEnabled, can } = useAuth();
  const setupRequired =
    scaffoldInFlight || (!!branding && (branding.setup_mode === true || branding.domain === ''));
  // Auth gate: se Postgres+auth abilitati, l'AuthContext bootstrap fa
  // refresh con cookie. Quando finisce e user è null → AuthPage.
  // Il bootstrap admin lifespan crea un account di default al primo
  // boot, password in `vault_root/logs/bootstrap_admin.txt`.
  //
  // Eccezione setup mode / Postgres off: `/auth/*` non è montato
  // (`authEnabled=false`) → la wiki è pubblica e shared, nessun login.
  // Senza questa guardia l'utente resta bloccato su AuthPage con la
  // registrazione chiusa e nessun backend a cui autenticarsi.
  const authGateRequired = authReady && user === null && authEnabled;
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

  // Invitation accept flow: URL ``/setup/invite?token=…`` (Fase 7+).
  // Maintainer ha emesso un invitation token via CLI. Cliente apre
  // l'URL, vede form set-password, attiva account. Token consumato
  // single-use server-side. Override: se already-logged ignoriamo
  // (trattato come URL vecchia mail aperta dopo).
  const inviteToken = !user ? new URLSearchParams(window.location.search).get('token') : null;
  const isInvitePath = window.location.pathname.startsWith('/setup/invite');
  if (!user && isInvitePath && inviteToken) {
    return (
      <>
        <AcceptInvite
          token={inviteToken}
          onComplete={() => setBootstrapPending(false)}
          onCancel={() => {
            window.history.replaceState({}, '', '/');
            window.location.reload();
          }}
        />
        <AppToaster styled={false} />
      </>
    );
  }

  // First-boot gate: se non c'è ancora alcun superuser, mostra il
  // BootstrapGate PRIMA di auth/setup. Self-checking via
  // /auth/bootstrap/status — se already-bootstrapped chiama subito
  // onComplete e si auto-smonta. Pattern best practice 2026:
  // Grafana / Vaultwarden first-time setup screen.
  if (!user && bootstrapPending) {
    return (
      <>
        <BootstrapGate onComplete={() => setBootstrapPending(false)} />
        <AppToaster styled={false} />
      </>
    );
  }

  // Force password change (Fase 7+ / NIST SP 800-63B): se il flag
  // ``must_change_password`` è True (es. password generata dal
  // bootstrap autostart, password reset admin-driven), blocca
  // qualsiasi altra UI finché l'utente non setta una nuova password.
  // Il backend rifiuta endpoint protetti con 403 in parallelo.
  if (user?.must_change_password) {
    return (
      <>
        <ForcePasswordChange
          onComplete={() => {
            /* logout reload */
          }}
        />
        <AppToaster styled={false} />
      </>
    );
  }

  // Auth gate PRIMA del wizard: il wizard chiama `/api/admin/*` che
  // richiede `role=admin` post-bootstrap (Fase 4). Senza login l'utente
  // vedrebbe wizard vuoto (401 sulle defaults). Forza login admin
  // quando users esistono — bootstrap admin ha sempre creato un account
  // di default al primo boot.
  if (authGateRequired) {
    return (
      <>
        <AuthPage />
        <AppToaster />
      </>
    );
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
    if (!user) {
      return <AuthPage />;
    }
    if (!can('graph.read')) {
      navigate('/');
      return null;
    }
    return <GraphPage />;
  }

  // Admin routes — full-page enterprise UI per gestione utenti / ruoli.
  // Gating: stesso permesso `admin.user.manage` esposto via Can() in header.
  // Senza permesso → redirect a `/` (silente).
  const adminRoute = locationPath.startsWith('/admin/users')
    ? 'users'
    : locationPath.startsWith('/admin/groups')
      ? 'groups'
      : locationPath.startsWith('/admin/roles')
        ? 'roles'
        : locationPath.startsWith('/admin/embeds')
          ? 'embeds'
          : locationPath.startsWith('/admin/feedback')
            ? 'feedback'
            : null;
  if (adminRoute) {
    if (!user) {
      return <AuthPage />;
    }
    const perms = user.permissions ?? [];
    const requiredPerm =
      adminRoute === 'groups'
        ? 'admin.group.manage'
        : adminRoute === 'embeds'
          ? 'admin.embed.manage'
          : adminRoute === 'feedback'
            ? 'feedback.read'
            : 'admin.user.manage';
    const canManage = user.role === 'admin' || perms.includes(requiredPerm);
    if (!canManage) {
      navigate('/', true);
      return null;
    }
    return (
      <>
        <AdminShell active={adminRoute}>
          {adminRoute === 'users' ? (
            <AdminUsersPage />
          ) : adminRoute === 'groups' ? (
            <AdminGroupsPage />
          ) : adminRoute === 'embeds' ? (
            <AdminEmbedsPage />
          ) : adminRoute === 'feedback' ? (
            <AdminFeedbackPage />
          ) : (
            <AdminRolesPage />
          )}
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
