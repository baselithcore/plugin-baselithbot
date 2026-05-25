import React, { memo, useState } from 'react';
import { createPortal } from 'react-dom';
import { ChevronsLeft, ChevronsRight, Link2, MessageSquare, Sparkles, XCircle } from 'lucide-react';
import ChatInput from './chat/ChatInput';
import ChatWindow from './chat/ChatWindow';
import ConversationHeader from './chat/ConversationHeader';
import ExamplePrompts from './chat/ExamplePrompts';
import JiraSection from './chat/JiraSection';
import SourcesSection from './chat/SourcesSection';
import { examplePrompts, useChatPanel } from './chat/useChatPanel';

const ChatPanel = () => {
  const {
    messages,
    conversationId,
    setConversationId,
    input,
    setInput,
    loading,
    generationStartTime,
    sources,
    jiraIssues,
    jiraExpanded,
    setJiraExpanded,
    error,
    copied,
    handleSend,
    handleActionClick,
    resetConversation,
    copyConversationId,
  } = useChatPanel();
  const [sideTab, setSideTab] = useState<'sources' | 'jira'>('sources');
  const [contextCollapsed, setContextCollapsed] = useState(true);
  const sessionLabel = conversationId ? conversationId.split('-')[0] || conversationId : '';
  const hasConversation = messages.length > 0;
  const contextItems = [
    { label: 'Fonti', value: sources.length },
    { label: 'Jira', value: jiraIssues.length },
    { label: 'Thread', value: messages.length },
  ];
  const contextToggleLabel = contextCollapsed ? 'Apri contesto' : 'Riduci contesto';

  const overviewItems = [
    {
      label: 'Stato thread',
      value: loading ? 'In elaborazione' : hasConversation ? 'Attivo' : 'Pronto',
      note: loading
        ? 'L’agente sta componendo la risposta.'
        : 'La vista resta centrata sul flusso della chat.',
      icon: <MessageSquare size={16} />,
    },
    {
      label: 'Messaggi',
      value: `${messages.length}`,
      note: hasConversation
        ? 'Scambio corrente mantenuto nello stesso thread.'
        : 'Ancora nessun messaggio inviato.',
      icon: <Sparkles size={16} />,
    },
    {
      label: 'Fonti',
      value: `${sources.length}`,
      note: sources.length
        ? 'Documenti e URL usati nell’ultima risposta.'
        : 'Nessuna fonte interrogata finora.',
      icon: <Link2 size={16} />,
    },
  ];

  return (
    <div className={`zen-conversation-layout ${contextCollapsed ? 'context-collapsed' : ''}`}>
      <section className="zen-chat-main">
        <header className="zen-header">
          <ConversationHeader
            conversationId={conversationId}
            onConversationIdChange={setConversationId}
            onCopyConversationId={copyConversationId}
            onResetConversation={resetConversation}
            copied={copied}
          />

          <button
            type="button"
            className="zen-context-trigger"
            onClick={() => setContextCollapsed((prev) => !prev)}
            aria-label={contextToggleLabel}
          >
            <Link2 size={18} />
            {sources.length + jiraIssues.length > 0 && (
              <span className="trigger-badge">{sources.length + jiraIssues.length}</span>
            )}
          </button>
        </header>

        <div className="zen-chat-body">
          {!hasConversation ? (
            <div className="zen-onboarding">
              <div className="zen-welcome-screen">
                <div className="zen-welcome-icon">
                  <Sparkles size={32} />
                </div>
                <h1>Agente Jira Intelligence</h1>
                <p>
                  Analizza documenti, gestisci issue e ottimizza i tuoi workflow con l'aiuto
                  dell'AI. Scegli un suggerimento o scrivi la tua richiesta sotto.
                </p>
                <ExamplePrompts prompts={examplePrompts} onSelect={setInput} />
              </div>
            </div>
          ) : (
            <ChatWindow
              messages={messages}
              onActionClick={handleActionClick}
              loading={loading}
              generationStartTime={generationStartTime}
            />
          )}
        </div>

        <footer className="zen-footer">
          <section className="zen-composer-wrapper">
            <ChatInput input={input} onChange={setInput} onSubmit={handleSend} loading={loading} />

            {error && (
              <div className="inline-alert zen-alert">
                <XCircle size={16} /> {error}
              </div>
            )}

            <div className="zen-composer-extras">
              <span className="tip-badge">
                <span className="key">Shift</span> + <span className="key">Invia</span> per andare a
                capo
              </span>
              {hasConversation && (
                <span className="tip-badge session">Thread ID: {conversationId.split('-')[0]}</span>
              )}
            </div>
          </section>
        </footer>
      </section>

      {createPortal(
        <aside
          id="conversation-context-panel"
          className={`zen-drawer ${contextCollapsed ? 'collapsed' : 'expanded'}`}
          aria-label="Contesto conversazione"
        >
          <div className="drawer-backdrop" onClick={() => setContextCollapsed(true)} />
          <div className="drawer-content">
            <div className="drawer-header">
              <div>
                <p className="eyebrow">Contesto</p>
                <h3>Fonti e Jira</h3>
              </div>
              <button
                type="button"
                className="ghost-icon"
                onClick={() => setContextCollapsed(true)}
              >
                <XCircle size={20} />
              </button>
            </div>

            <div className="drawer-tabs">
              <button
                type="button"
                className={`side-tab ${sideTab === 'sources' ? 'active' : ''}`}
                onClick={() => setSideTab('sources')}
              >
                <Link2 size={14} /> Fonti ({sources.length})
              </button>
              <button
                type="button"
                className={`side-tab ${sideTab === 'jira' ? 'active' : ''}`}
                onClick={() => setSideTab('jira')}
              >
                <Sparkles size={14} /> Jira ({jiraIssues.length})
              </button>
            </div>

            <div className="drawer-scroll-area">
              {sideTab === 'sources' ? (
                <SourcesSection sources={sources} layout="panel" />
              ) : (
                <JiraSection
                  issues={jiraIssues}
                  expanded={jiraExpanded}
                  onToggleExpanded={() => setJiraExpanded(!jiraExpanded)}
                  layout="panel"
                />
              )}
            </div>
          </div>
        </aside>,
        document.body
      )}
    </div>
  );
};

export default memo(ChatPanel);
