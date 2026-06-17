import { useEffect, useState } from 'react';
import { GlassPanel } from '../components/GlassPanel';
import { Skeleton } from '../components/Skeleton';
import { api } from '../lib/api';
import type { ModelInfo } from '../lib/types';

/** Provider catalogue: which coding backends agents can route to. */
export function Models() {
  const [models, setModels] = useState<ModelInfo[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .models()
      .then(setModels)
      .catch((e) => setError((e as Error).message));
  }, []);

  if (error)
    return (
      <GlassPanel title="Models">
        <p className="text-rose-400">{error}</p>
      </GlassPanel>
    );
  if (!models) return <Skeleton height={180} />;

  return (
    <GlassPanel title="Model providers" subtitle="Claude, OpenAI, and local Ollama backends.">
      <div className="grid gap-4 sm:grid-cols-3">
        {models.map((m) => (
          <div key={m.provider} className="rounded-xl border border-ink-600/50 bg-ink-800/40 p-4">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold capitalize text-slate-100">{m.provider}</h3>
              <span
                className={`rounded-md px-2 py-0.5 text-[10px] font-medium ${
                  m.local ? 'bg-cyan/15 text-cyan' : 'bg-iris/15 text-iris'
                }`}
              >
                {m.local ? 'local' : 'cloud'}
              </span>
            </div>
            <p className="mt-2 font-mono text-xs text-slate-400">{m.default_model}</p>
            <p className="mt-3 text-[11px] text-slate-500">
              {m.requires_api_key ? 'Requires LLM_API_KEY' : 'No API key required'}
            </p>
          </div>
        ))}
      </div>
    </GlassPanel>
  );
}
