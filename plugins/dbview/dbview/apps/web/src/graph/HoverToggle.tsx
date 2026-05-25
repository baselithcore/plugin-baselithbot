import type { ReactNode } from 'react';
import { Sparkles, Wand2, ZapOff } from 'lucide-react';
import { cn } from '../lib/cn.js';
import type { HoverMode } from './hover-guard.js';

interface Props {
  mode: HoverMode;
  enabled: boolean;
  onChange: (m: HoverMode) => void;
  /** Bottom offset in px so multiple toolbars can stack without overlap. */
  bottomPx?: number;
}

export function HoverToggle({ mode, enabled, onChange, bottomPx = 12 }: Props) {
  const items: Array<{ mode: HoverMode; icon: ReactNode; label: string; title: string }> = [
    {
      mode: 'auto',
      icon: <Wand2 className="w-3.5 h-3.5" />,
      label: 'Auto',
      title:
        'Auto: highlight neighborhood on small graphs, disable on dense ones to keep navigation smooth',
    },
    {
      mode: 'on',
      icon: <Sparkles className="w-3.5 h-3.5" />,
      label: 'On',
      title: 'Always highlight on hover',
    },
    {
      mode: 'off',
      icon: <ZapOff className="w-3.5 h-3.5" />,
      label: 'Off',
      title: 'Disable hover highlight — click a node to inspect',
    },
  ];
  return (
    <div
      role="radiogroup"
      aria-label="Hover highlight"
      className="absolute right-3 z-10 panel-glass segmented h-9"
      style={{ bottom: bottomPx }}
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
            title={
              it.mode === 'auto' && !enabled
                ? `${it.title} · currently off (large graph)`
                : it.title
            }
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
