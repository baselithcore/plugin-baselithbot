import { useEffect, useRef, useState } from 'react';
import { Button } from './Button';
import { Icon } from './Icon';
import { Modal } from './Modal';

type Tone = 'danger' | 'warn' | 'neutral';

interface ConfirmDialogProps {
  open: boolean;
  onClose: () => void;
  onConfirm: () => void | Promise<void>;
  title: string;
  description?: React.ReactNode;
  /** Optional list of destructive consequences shown as bullets. */
  consequences?: React.ReactNode[];
  /** When set, the user must type this string verbatim before confirming. */
  confirmText?: string;
  confirmLabel?: string;
  cancelLabel?: string;
  tone?: Tone;
  busy?: boolean;
  /** Optional checkbox the operator must tick before confirming. */
  acknowledgement?: string;
}

const TONE_RING: Record<Tone, string> = {
  danger: 'text-sev-critical bg-sev-critical/10 ring-sev-critical/30',
  warn: 'text-accent-warn bg-accent-warn/10 ring-accent-warn/30',
  neutral: 'text-text-secondary bg-bg-overlay ring-bg-line',
};

export function ConfirmDialog({
  open,
  onClose,
  onConfirm,
  title,
  description,
  consequences,
  confirmText,
  confirmLabel = 'Confirm',
  cancelLabel = 'Cancel',
  tone = 'danger',
  busy = false,
  acknowledgement,
}: ConfirmDialogProps) {
  const [typed, setTyped] = useState('');
  const [acked, setAcked] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    if (open) {
      setTyped('');
      setAcked(false);
      setError(null);
      // Defer focus so the modal portal mounts first.
      const t = setTimeout(() => inputRef.current?.focus(), 30);
      return () => clearTimeout(t);
    }
  }, [open]);

  const matchOk = !confirmText || typed.trim() === confirmText;
  const ackOk = !acknowledgement || acked;
  const canConfirm = matchOk && ackOk && !busy;

  async function handleConfirm() {
    if (!canConfirm) return;
    try {
      await onConfirm();
    } catch (e) {
      setError(String(e));
    }
  }

  return (
    <Modal open={open} onClose={busy ? () => {} : onClose} size="md" ariaLabel={title}>
      <div className="p-6">
        <div className="flex items-start gap-3">
          <div
            className={`grid h-10 w-10 shrink-0 place-items-center rounded-md ring-1 ${TONE_RING[tone]}`}
          >
            <Icon.AlertTriangle size={18} />
          </div>
          <div className="min-w-0 flex-1">
            <h2 className="font-display text-lg font-medium text-text-primary">{title}</h2>
            {description && <p className="mt-1 text-sm text-text-secondary">{description}</p>}
          </div>
        </div>

        {consequences && consequences.length > 0 && (
          <ul className="mt-4 space-y-1.5 rounded-md border border-bg-line bg-bg-overlay/40 p-3 text-sm text-text-secondary">
            {consequences.map((c, i) => (
              <li key={i} className="flex items-start gap-2">
                <span className="mt-1 h-1 w-1 shrink-0 rounded-full bg-sev-critical" />
                <span>{c}</span>
              </li>
            ))}
          </ul>
        )}

        {confirmText && (
          <div className="mt-5">
            <label className="block text-2xs font-mono uppercase tracking-wider text-text-muted">
              Type{' '}
              <code className="rounded bg-bg-overlay px-1.5 py-0.5 text-text-primary ring-1 ring-bg-line">
                {confirmText}
              </code>{' '}
              to confirm
            </label>
            <input
              ref={inputRef}
              value={typed}
              onChange={(e) => setTyped(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && canConfirm) handleConfirm();
              }}
              className="ra-input mt-2 w-full font-mono"
              spellCheck={false}
              autoComplete="off"
              disabled={busy}
            />
          </div>
        )}

        {acknowledgement && (
          <label className="mt-4 flex items-start gap-2 text-sm text-text-secondary">
            <input
              type="checkbox"
              checked={acked}
              onChange={(e) => setAcked(e.target.checked)}
              className="mt-1 accent-sev-critical"
              disabled={busy}
            />
            <span>{acknowledgement}</span>
          </label>
        )}

        {error && (
          <div className="mt-4 rounded border border-sev-critical/40 bg-sev-critical/10 px-3 py-2 text-sm text-sev-critical">
            {error}
          </div>
        )}

        <div className="mt-6 flex justify-end gap-2">
          <Button variant="ghost" onClick={onClose} disabled={busy}>
            {cancelLabel}
          </Button>
          <Button
            variant={tone === 'danger' ? 'danger' : 'primary'}
            onClick={handleConfirm}
            disabled={!canConfirm}
          >
            {busy ? 'Working…' : confirmLabel}
          </Button>
        </div>
      </div>
    </Modal>
  );
}
