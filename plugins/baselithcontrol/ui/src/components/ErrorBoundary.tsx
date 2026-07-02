import { Component, type ReactNode } from 'react';
import { useTranslation } from 'react-i18next';
import { AlertTriangle, RotateCcw } from 'lucide-react';

interface BoundaryProps {
  children: ReactNode;
  /** Remount marker: when it changes (e.g. tab switch), a crashed page resets. */
  resetKey: string;
  t: (key: string) => string;
}

interface BoundaryState {
  failed: boolean;
}

// Class-based boundary (React exposes componentDidCatch only on classes).
class Boundary extends Component<BoundaryProps, BoundaryState> {
  state: BoundaryState = { failed: false };

  static getDerivedStateFromError(): BoundaryState {
    return { failed: true };
  }

  componentDidCatch(error: unknown): void {
    // Surface the crash for operators/devtools; the UI already degraded softly.
    console.error('[baselithcontrol] page crashed:', error);
  }

  componentDidUpdate(prev: BoundaryProps): void {
    // Navigating to another tab replaces the crashed subtree → try again.
    if (this.state.failed && prev.resetKey !== this.props.resetKey) {
      this.setState({ failed: false });
    }
  }

  render(): ReactNode {
    if (!this.state.failed) return this.props.children;
    const { t } = this.props;
    return (
      <div className="glass mx-auto mt-16 flex max-w-md flex-col items-center gap-3 p-8 text-center">
        <span className="flex h-11 w-11 items-center justify-center rounded-lg bg-rose-500/10 text-rose-500">
          <AlertTriangle className="h-5 w-5" />
        </span>
        <h2 className="text-[15px] font-semibold t-primary">{t('error.title')}</h2>
        <p className="text-[12px] leading-relaxed t-dim">{t('error.body')}</p>
        <button
          type="button"
          onClick={() => this.setState({ failed: false })}
          className="btn-primary mt-2 inline-flex items-center gap-1.5 rounded-lg px-3.5 py-2 text-[12px] font-semibold"
        >
          <RotateCcw className="h-3.5 w-3.5" />
          {t('error.retry')}
        </button>
      </div>
    );
  }
}

/**
 * Localized error boundary wrapped around each tab's page content so a crash
 * in one page cannot blank the whole dashboard shell (topbar, toasts, dialogs
 * stay alive). The retry button re-renders the failed subtree in place.
 */
export function ErrorBoundary({ children, resetKey }: { children: ReactNode; resetKey: string }) {
  const { t } = useTranslation();
  return (
    <Boundary resetKey={resetKey} t={(key) => t(key)}>
      {children}
    </Boundary>
  );
}
