import { Component, type ErrorInfo, type ReactNode } from 'react';
import { AlertTriangle, RotateCcw } from 'lucide-react';

interface Props {
  children: ReactNode;
}

interface State {
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    // eslint-disable-next-line no-console
    console.error('UI crash:', error, info);
  }

  reset = () => {
    this.setState({ error: null });
  };

  reload = () => {
    window.location.reload();
  };

  render() {
    if (!this.state.error) return this.props.children;
    const err = this.state.error;
    return (
      <div className="min-h-screen bg-canvas text-ink grid place-items-center px-6">
        <div role="alert" className="surface max-w-lg p-6 flex flex-col items-start gap-3">
          <div className="inline-flex items-center gap-2 text-[var(--color-danger)]">
            <AlertTriangle size={16} />
            <span className="text-sm font-semibold uppercase">Errore applicativo</span>
          </div>
          <p className="text-sm text-ink-muted leading-relaxed">
            L'interfaccia ha incontrato un errore imprevisto. Puoi riprovare senza perdere la
            cronologia (salvata localmente) oppure ricaricare la pagina.
          </p>
          <pre className="w-full text-[11px] bg-[var(--color-surface)] border border-[var(--color-border)] rounded-md p-2 overflow-x-auto">
            {err.name}: {err.message}
          </pre>
          <div className="flex items-center gap-2">
            <button
              onClick={this.reset}
              className="focus-ring inline-flex items-center gap-1.5 rounded-md
                         border border-[var(--color-border)] bg-[var(--color-canvas-raised)]
                         px-3 py-1.5 text-xs font-medium hover:border-[var(--color-brand-ring)]"
            >
              <RotateCcw size={12} /> Riprova
            </button>
            <button
              onClick={this.reload}
              className="focus-ring inline-flex items-center gap-1.5 rounded-md
                         bg-[var(--color-brand)] text-white
                         px-3 py-1.5 text-xs font-medium hover:bg-[var(--color-brand-strong)]"
            >
              Ricarica pagina
            </button>
          </div>
        </div>
      </div>
    );
  }
}
