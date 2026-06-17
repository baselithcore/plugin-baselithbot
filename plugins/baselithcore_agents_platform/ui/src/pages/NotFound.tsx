import { Link } from 'react-router-dom';
import { GlassPanel } from '../components/GlassPanel';

export function NotFound() {
  return (
    <GlassPanel title="Not found">
      <p className="text-sm text-slate-400">That route does not exist.</p>
      <Link to="/" className="mt-3 inline-block text-sm text-cyan hover:underline">
        ← Back to Builder
      </Link>
    </GlassPanel>
  );
}
