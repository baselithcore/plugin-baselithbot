import { lazy, Suspense } from 'react';
import type { RenderProps } from './style';

export type GraphMode = '2d' | '3d';

// Each renderer is its own lazy chunk so the heavy Three.js (3D) bundle only
// downloads when the user actually switches to the 3D view — the 2D path stays
// light. Honors the plugin's lazy-loading rule for large graph assets.
const Canvas2D = lazy(() => import('./Canvas2D').then((m) => ({ default: m.Canvas2D })));
const Canvas3D = lazy(() => import('./Canvas3D').then((m) => ({ default: m.Canvas3D })));

interface Props extends RenderProps {
  mode?: GraphMode;
}

/** Renderer dispatcher: picks the 2D or 3D force graph by `mode` (default 2D). */
export function GraphView({ mode = '2d', ...props }: Props) {
  return (
    <Suspense fallback={<Fallback />}>
      {mode === '3d' ? <Canvas3D {...props} /> : <Canvas2D {...props} />}
    </Suspense>
  );
}

function Fallback() {
  return (
    <div className="flex h-full items-center justify-center text-sm text-[var(--color-faint)]">
      Loading graph…
    </div>
  );
}
