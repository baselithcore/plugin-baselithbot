import type { ReactNode } from 'react';
import { Box, Eye, EyeOff, Network, Share2, Sparkles, Wand2, ZapOff } from 'lucide-react';
import { cn } from '../../../lib/cn';
import type { HoverMode } from './useHoverGuard';

export type LabelMode = 'off' | 'hubs' | 'all';
export type ViewMode = '2d' | '3d' | 'cose';

const OVERLAY_BASE =
  'absolute z-10 rounded-xl border border-[var(--color-border)] bg-canvas-raised/90 backdrop-blur ' +
  'shadow-sm text-[10.5px] font-mono text-ink-muted pointer-events-auto';

const SEGMENTED_ITEM =
  'inline-flex items-center gap-1 px-2.5 py-1.5 text-[10.5px] font-medium ' +
  'text-ink-muted hover:text-ink transition-colors first:rounded-l-xl last:rounded-r-xl';

const SEGMENTED_ITEM_ACTIVE = 'bg-accent/15 text-ink';

interface SegmentedButtonProps {
  active: boolean;
  onClick: () => void;
  title: string;
  ariaChecked: boolean;
  children: ReactNode;
}

function SegmentedButton({ active, onClick, title, ariaChecked, children }: SegmentedButtonProps) {
  return (
    <button
      type="button"
      role="radio"
      aria-checked={ariaChecked}
      onClick={onClick}
      title={title}
      className={cn(SEGMENTED_ITEM, active && SEGMENTED_ITEM_ACTIVE)}
    >
      {children}
    </button>
  );
}

interface LegendProps {
  nodes: number;
  edges: number;
  hint?: string;
}

export function Legend({ nodes, edges, hint }: LegendProps) {
  return (
    <div
      className={cn(OVERLAY_BASE, 'bottom-3 left-3 flex items-center gap-2 px-3 py-1.5')}
      role="status"
      aria-live="off"
    >
      <span className="text-ink">{nodes}</span>
      <span>nodi</span>
      <span className="text-ink-subtle">·</span>
      <span className="text-ink">{edges}</span>
      <span>archi</span>
      {hint && (
        <>
          <span className="text-ink-subtle">·</span>
          <span className="text-ink-subtle">{hint}</span>
        </>
      )}
    </div>
  );
}

interface LabelToggleProps {
  mode: LabelMode;
  onChange: (m: LabelMode) => void;
  bottomPx?: number;
}

export function LabelToggle({ mode, onChange, bottomPx = 12 }: LabelToggleProps) {
  const items: Array<{ mode: LabelMode; icon: ReactNode; label: string; title: string }> = [
    { mode: 'off', icon: <EyeOff size={12} />, label: 'Off', title: 'Nasconde tutte le etichette' },
    {
      mode: 'hubs',
      icon: <Sparkles size={12} />,
      label: 'Hub',
      title: 'Solo etichette dei nodi più connessi (top decile)',
    },
    {
      mode: 'all',
      icon: <Eye size={12} />,
      label: 'Tutti',
      title: 'Tutte le etichette (zoom-in per i dettagli)',
    },
  ];
  return (
    <div
      role="radiogroup"
      aria-label="Visibilità etichette"
      className={cn(OVERLAY_BASE, 'right-3 flex items-center')}
      style={{ bottom: bottomPx }}
    >
      {items.map((it) => (
        <SegmentedButton
          key={it.mode}
          active={mode === it.mode}
          ariaChecked={mode === it.mode}
          onClick={() => onChange(it.mode)}
          title={it.title}
        >
          {it.icon}
          {it.label}
        </SegmentedButton>
      ))}
    </div>
  );
}

interface HoverToggleProps {
  mode: HoverMode;
  enabled: boolean;
  onChange: (m: HoverMode) => void;
  bottomPx?: number;
}

export function HoverToggle({ mode, enabled, onChange, bottomPx = 56 }: HoverToggleProps) {
  const items: Array<{ mode: HoverMode; icon: ReactNode; label: string; title: string }> = [
    {
      mode: 'auto',
      icon: <Wand2 size={12} />,
      label: 'Auto',
      title:
        'Auto: highlight del vicinato sui grafi piccoli, disattivato su quelli densi per non disturbare la navigazione',
    },
    {
      mode: 'on',
      icon: <Sparkles size={12} />,
      label: 'On',
      title: 'Highlight sempre attivo su hover',
    },
    {
      mode: 'off',
      icon: <ZapOff size={12} />,
      label: 'Off',
      title: 'Highlight disattivato — clicca un nodo per ispezionarlo',
    },
  ];
  return (
    <div
      role="radiogroup"
      aria-label="Highlight hover"
      className={cn(OVERLAY_BASE, 'right-3 flex items-center')}
      style={{ bottom: bottomPx }}
    >
      {items.map((it) => (
        <SegmentedButton
          key={it.mode}
          active={mode === it.mode}
          ariaChecked={mode === it.mode}
          onClick={() => onChange(it.mode)}
          title={
            it.mode === 'auto' && !enabled
              ? `${it.title} · attualmente off (grafo denso)`
              : it.title
          }
        >
          {it.icon}
          {it.label}
        </SegmentedButton>
      ))}
    </div>
  );
}

interface ViewModeToggleProps {
  mode: ViewMode;
  onChange: (m: ViewMode) => void;
}

export function ViewModeToggle({ mode, onChange }: ViewModeToggleProps) {
  const items: Array<{ mode: ViewMode; icon: ReactNode; label: string; title: string }> = [
    {
      mode: '2d',
      icon: <Share2 size={12} />,
      label: '2D',
      title: '2D force-directed (react-force-graph-2d) — denso, scorrevole',
    },
    {
      mode: '3d',
      icon: <Box size={12} />,
      label: '3D',
      title: '3D force-directed (three.js) — esplorazione spaziale',
    },
    {
      mode: 'cose',
      icon: <Network size={12} />,
      label: 'Layout',
      title: 'Cytoscape cose-bilkent — layout deterministico stabile fra reload',
    },
  ];
  return (
    <div
      role="radiogroup"
      aria-label="Modalità di visualizzazione"
      className={cn(OVERLAY_BASE, 'top-3 right-3 flex items-center')}
    >
      {items.map((it) => (
        <SegmentedButton
          key={it.mode}
          active={mode === it.mode}
          ariaChecked={mode === it.mode}
          onClick={() => onChange(it.mode)}
          title={it.title}
        >
          {it.icon}
          {it.label}
        </SegmentedButton>
      ))}
    </div>
  );
}
