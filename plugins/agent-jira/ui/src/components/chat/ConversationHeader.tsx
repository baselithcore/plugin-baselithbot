import { Check, Copy, RefreshCw, MessageSquare } from 'lucide-react';

type ConversationHeaderProps = {
  conversationId: string;
  onConversationIdChange: (value: string) => void;
  onCopyConversationId: () => void;
  onResetConversation: () => void;
  copied: boolean;
};

const ConversationHeader = ({
  conversationId,
  onConversationIdChange,
  onCopyConversationId,
  onResetConversation,
  copied,
}: ConversationHeaderProps) => (
  <div className="zen-header-compact">
    <div className="header-info">
      <div className="header-title-row">
        <MessageSquare size={18} className="muted" />
        <h3>Conversazione</h3>
        <span className="badge-persistent">AI Agent</span>
      </div>
      <p className="header-subtitle">
        Parla con l'agente per gestire issue, sprint e documentazione.
      </p>
    </div>

    <div className="header-controls">
      <div
        className="session-id-wrapper"
        onClick={(e) => {
          if (e.target instanceof HTMLInputElement) return;
          onCopyConversationId();
        }}
        title="ID Sessione (clicca per copiare)"
      >
        <label>ID</label>
        <input
          value={conversationId}
          onChange={(e) => onConversationIdChange(e.target.value.trim())}
          spellCheck={false}
          placeholder="Crea o incolla ID"
          aria-label="Conversation ID"
        />
        <div className="icon-btn-sm">{copied ? <Check size={14} /> : <Copy size={14} />}</div>
      </div>

      <button
        type="button"
        className="ghost-sm"
        onClick={onResetConversation}
        title="Resetta e avvia nuova sessione"
      >
        <RefreshCw size={14} />
        <span>Nuova</span>
      </button>
    </div>
  </div>
);

export default ConversationHeader;
