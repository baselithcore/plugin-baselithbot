import { AlertTriangle, CheckCircle2, Loader2, MessageSquareText, Sparkles } from 'lucide-react';
import { cn } from '../../lib/cn.js';
import type { ChatTurn } from './turn-types.js';

interface Props {
  turn: ChatTurn;
  isWorking: boolean;
  statusCopy: Record<ChatTurn['status'], string>;
}

export function AssistantTurnHeader({ turn, isWorking, statusCopy }: Props) {
  const isError = turn.status === 'error';
  const createdAt = new Date(turn.createdAt).toLocaleTimeString([], {
    hour: '2-digit',
    minute: '2-digit',
  });

  return (
    <div
      className={cn(
        'flex items-start justify-between gap-3 border-b border-border-subtle px-3 py-2.5',
        isError ? 'bg-danger/5' : 'bg-surface-2/30',
      )}
    >
      <div className="flex min-w-0 items-start gap-2.5">
        <div
          className={cn(
            'mt-0.5 grid h-7 w-7 shrink-0 place-items-center rounded-md border',
            isError
              ? 'border-danger/25 bg-danger/10 text-danger'
              : 'border-accent/25 bg-accent/10 text-accent',
          )}
        >
          <MessageSquareText className="h-3.5 w-3.5" />
        </div>
        <div className="min-w-0">
          <div className="truncate text-[13px] font-semibold leading-5" title={turn.prompt}>
            {turn.prompt}
          </div>
          <div className="mt-0.5 flex flex-wrap items-center gap-1.5 text-[11px] text-text-dim">
            <span>{createdAt}</span>
            <span className="h-1 w-1 rounded-full bg-border" />
            <span>{turn.mode === 'ask' ? 'Ask' : 'Draft'}</span>
          </div>
        </div>
      </div>
      <span
        key={turn.status}
        className={cn(
          'chip h-6 shrink-0 px-2 text-[10px]',
          turn.status === 'ready' && 'chip-success pulse-once',
          isError && 'chip-danger',
        )}
      >
        {isWorking ? (
          <Loader2 className="h-3 w-3 animate-spin" />
        ) : isError ? (
          <AlertTriangle className="h-3 w-3" />
        ) : turn.status === 'ready' ? (
          <CheckCircle2 className="h-3 w-3" />
        ) : (
          <Sparkles className="h-3 w-3" />
        )}
        {isError ? 'Error' : statusCopy[turn.status]}
      </span>
    </div>
  );
}
