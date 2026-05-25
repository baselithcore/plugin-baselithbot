import { Check, Copy } from 'lucide-react';
import { useCopyToClipboard } from '../../hooks/useCopyToClipboard';

interface CopyButtonProps {
  text: string;
  label?: string;
}

export function CopyButton({ text, label }: CopyButtonProps) {
  const { copiedText, copy } = useCopyToClipboard();
  const isCopied = copiedText === text;

  return (
    <button
      className={`copy-btn ${isCopied ? 'copied' : ''}`}
      onClick={(e) => {
        e.stopPropagation();
        copy(text);
      }}
      title={label || 'Copy to clipboard'}
    >
      {isCopied ? <Check size={12} /> : <Copy size={12} />}
    </button>
  );
}
