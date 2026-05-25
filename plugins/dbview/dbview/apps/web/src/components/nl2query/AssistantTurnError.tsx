import { AlertTriangle, Cpu, RotateCcw } from 'lucide-react';
import { useAppStore } from '../../store/app.js';
import { classifyError } from './assistant-turn-errors.js';

interface Props {
  message: string;
  onRetry: () => void;
}

export function AssistantTurnError({ message, onRetry }: Props) {
  const provider = useAppStore((s) => s.provider);
  const { title, hint, showModelPicker } = classifyError(message, provider);

  // The model picker now lives in the composer toolbar (Claude-style). We
  // dispatch a custom event the composer listens for and opens the picker,
  // rather than scrolling/focusing imperatively across components.
  const focusModelPicker = () => {
    window.dispatchEvent(new CustomEvent('dbview:open-model-picker'));
  };

  return (
    <div
      className="px-3 py-3 flex items-start gap-2.5 border-b text-[12px]"
      style={{
        borderColor: 'rgb(var(--border-subtle))',
        background: 'rgb(var(--danger) / 0.06)',
      }}
    >
      <AlertTriangle className="w-3.5 h-3.5 mt-0.5 shrink-0 text-danger" />
      <div className="flex-1 min-w-0 flex flex-col gap-1">
        <div className="font-semibold text-danger">{title}</div>
        <div className="text-[11px] text-text-muted break-words">{message}</div>
        {hint && <div className="text-[11px] text-text-muted">{hint}</div>}
        {showModelPicker && (
          <button
            onClick={focusModelPicker}
            className="inline-flex items-center gap-1 text-[11px] self-start text-accent hover:text-accent/80 mt-0.5 underline-offset-2 hover:underline"
          >
            <Cpu className="w-3 h-3" />
            Pick another model
          </button>
        )}
      </div>
      <button onClick={onRetry} className="btn-ghost h-7 px-2 shrink-0" title="Retry this turn">
        <RotateCcw className="w-3.5 h-3.5" />
        Retry
      </button>
    </div>
  );
}
