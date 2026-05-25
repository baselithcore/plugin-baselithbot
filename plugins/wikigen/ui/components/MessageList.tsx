import { useEffect, useRef } from 'react';
import type { Message } from '../lib/types';
import { ChatMessage } from './Message';

interface Props {
  messages: Message[];
  onPickSource: (docId: string, anchor?: string) => void;
  onOpenSources: () => void;
  editionLabel?: string | null;
  onRegenerate?: () => void;
  onEdit?: (messageId: string, content: string) => void;
  isStreaming?: boolean;
  showTrace?: boolean;
  showTimer?: boolean;
  feedbackEnabled?: boolean;
}

export function MessageList({
  messages,
  onPickSource,
  onOpenSources,
  editionLabel,
  onRegenerate,
  onEdit,
  isStreaming,
  showTrace,
  showTimer,
  feedbackEnabled,
}: Props) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
  }, [messages]);

  // Ultimo assistant e ultimo user — abilitati a regenerate/edit
  let lastAssistantIdx = -1;
  let lastUserIdx = -1;
  for (let i = messages.length - 1; i >= 0; i--) {
    if (lastAssistantIdx === -1 && messages[i].role === 'assistant') lastAssistantIdx = i;
    if (lastUserIdx === -1 && messages[i].role === 'user') lastUserIdx = i;
    if (lastAssistantIdx !== -1 && lastUserIdx !== -1) break;
  }

  return (
    <div className="flex-1 overflow-y-auto" role="log" aria-label="cronologia messaggi">
      <div className="mx-auto max-w-3xl">
        {messages.map((m, i) => {
          // Trova user più recente che precede questo assistant (per telemetria feedback)
          let pairedQuestion: string | undefined;
          if (m.role === 'assistant') {
            for (let j = i - 1; j >= 0; j--) {
              if (messages[j].role === 'user') {
                pairedQuestion = messages[j].content;
                break;
              }
            }
          }
          return (
            <ChatMessage
              key={m.id}
              message={m}
              isLast={i === messages.length - 1}
              onPickSource={onPickSource}
              onOpenSources={onOpenSources}
              editionLabel={editionLabel}
              onRegenerate={
                i === lastAssistantIdx && !isStreaming && onRegenerate ? onRegenerate : undefined
              }
              onEdit={i === lastUserIdx && !isStreaming && onEdit ? onEdit : undefined}
              showTrace={showTrace}
              showTimer={showTimer}
              pairedQuestion={pairedQuestion}
              feedbackEnabled={feedbackEnabled}
            />
          );
        })}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}
