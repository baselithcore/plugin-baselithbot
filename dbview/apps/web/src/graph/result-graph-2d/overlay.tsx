import type { ReactNode } from 'react';
import { Eye, EyeOff, Sparkles } from 'lucide-react';
import { cn } from '../../lib/cn.js';
import type { LabelMode } from './types.js';

export function Legend({ nodes, edges }: { nodes: number; edges: number }) {
  return (
    <div className="absolute bottom-3 left-3 panel-glass px-3 py-1.5 text-[10px] font-mono text-text-muted flex items-center gap-2 z-10 pointer-events-none">
      <span>{nodes} nodes</span>
      <span className="text-text-dim">·</span>
      <span>{edges} rel</span>
      <span className="text-text-dim">·</span>
      <span className="text-text-dim">hover for label</span>
    </div>
  );
}

interface LabelToggleProps {
  mode: LabelMode;
  onChange: (m: LabelMode) => void;
}

export function LabelToggle({ mode, onChange }: LabelToggleProps) {
  const items: Array<{ mode: LabelMode; icon: ReactNode; title: string; label: string }> = [
    {
      mode: 'off',
      icon: <EyeOff className="w-3.5 h-3.5" />,
      title: 'Hide all labels',
      label: 'Off',
    },
    {
      mode: 'hubs',
      icon: <Sparkles className="w-3.5 h-3.5" />,
      title: 'Show only hub labels (top by degree)',
      label: 'Hubs',
    },
    {
      mode: 'all',
      icon: <Eye className="w-3.5 h-3.5" />,
      title: 'Show all labels (when zoomed in)',
      label: 'All',
    },
  ];
  return (
    <div
      role="radiogroup"
      aria-label="Label visibility"
      className="absolute bottom-3 right-3 z-10 panel-glass segmented h-9"
    >
      {items.map((it) => {
        const active = mode === it.mode;
        return (
          <button
            key={it.mode}
            type="button"
            role="radio"
            aria-checked={active}
            onClick={() => onChange(it.mode)}
            title={it.title}
            className={cn(
              'segmented-item font-mono text-[10px]',
              active && 'segmented-item-active',
            )}
          >
            {it.icon}
            {it.label}
          </button>
        );
      })}
    </div>
  );
}
