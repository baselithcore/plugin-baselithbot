import { FormEvent, KeyboardEvent, useEffect, useRef } from 'react';
import { ArrowUp, Sparkles } from 'lucide-react';

type ChatInputProps = {
  input: string;
  onChange: (value: string) => void;
  onSubmit: (evt?: FormEvent) => void;
  loading: boolean;
};

const ChatInput = ({ input, onChange, onSubmit, loading }: ChatInputProps) => {
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (textareaRef.current && textareaRef.current.scrollHeight > 0) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${textareaRef.current.scrollHeight}px`;
    }
  }, [input]);

  const handleKeyDown = (evt: KeyboardEvent<HTMLTextAreaElement>) => {
    if (evt.key !== 'Enter' || evt.shiftKey) return;
    evt.preventDefault();
    if (!input.trim() || loading) return;
    onSubmit();
  };

  return (
    <form
      className="zen-chat-input"
      onSubmit={(e) => {
        e.preventDefault();
        if (input.trim() && !loading) onSubmit();
      }}
    >
      <textarea
        ref={textareaRef}
        value={input}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Chiedi qualsiasi cosa all'Agente Jira..."
        rows={1}
      />
      <button
        type="submit"
        className="zen-send-btn"
        disabled={loading || !input.trim()}
        title="Invia messaggio"
      >
        {loading ? <Sparkles className="spin" size={18} /> : <ArrowUp size={20} />}
      </button>
    </form>
  );
};

export default ChatInput;
