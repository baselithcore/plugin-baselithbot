import { Toaster } from 'sonner';

const TOAST_STYLE = {
  background: 'var(--color-canvas-raised)',
  color: 'var(--color-ink)',
  border: '1px solid var(--color-border)',
  fontSize: '13px',
  borderRadius: '12px',
} as const;

export function AppToaster({ styled = true }: { styled?: boolean }) {
  if (!styled) {
    return <Toaster theme="system" position="top-right" />;
  }
  return (
    <Toaster
      theme="system"
      position="top-right"
      toastOptions={{ style: TOAST_STYLE }}
    />
  );
}
