import { Info, Map } from 'lucide-react';
import { cn } from '../../lib/cn.js';

interface Props {
  minimapVisible: boolean;
  legendVisible: boolean;
  onToggleMinimap: () => void;
  onToggleLegend: () => void;
  /** Hide the minimap toggle when no minimap is available (e.g. table-only views). */
  canToggleMinimap?: boolean;
  /** Hide the legend toggle when the legend itself is not rendered for this kind. */
  canToggleLegend?: boolean;
}

/**
 * Floating toggle stack rendered above the React Flow zoom Controls in the
 * bottom-right corner. Each toggle is a small icon button mirroring the
 * `toolbar-surface` styling used by the top Toolbar, so the controls feel
 * unified across the canvas.
 */
export function ViewToggles({
  minimapVisible,
  legendVisible,
  onToggleMinimap,
  onToggleLegend,
  canToggleMinimap = true,
  canToggleLegend = true,
}: Props) {
  if (!canToggleMinimap && !canToggleLegend) return null;
  return (
    <div
      className="absolute right-2 z-10 flex flex-col items-end gap-1"
      // 150px clears the Controls vertical stack (zoom in/out/fit/lock at 35px
      // each plus padding) on every breakpoint @xyflow/react renders today.
      style={{ bottom: 150 }}
    >
      {canToggleLegend && (
        <button
          type="button"
          onClick={onToggleLegend}
          className={cn(
            'toolbar-surface btn-icon w-8 h-8 transition-colors',
            legendVisible ? 'text-accent' : 'text-text-muted',
          )}
          aria-label={legendVisible ? 'Hide legend' : 'Show legend'}
          aria-pressed={legendVisible}
          title={legendVisible ? 'Hide legend' : 'Show legend'}
        >
          <Info className="w-3.5 h-3.5" />
        </button>
      )}
      {canToggleMinimap && (
        <button
          type="button"
          onClick={onToggleMinimap}
          className={cn(
            'toolbar-surface btn-icon w-8 h-8 transition-colors',
            minimapVisible ? 'text-accent' : 'text-text-muted',
          )}
          aria-label={minimapVisible ? 'Hide minimap' : 'Show minimap'}
          aria-pressed={minimapVisible}
          title={minimapVisible ? 'Hide minimap' : 'Show minimap'}
        >
          <Map className="w-3.5 h-3.5" />
        </button>
      )}
    </div>
  );
}
