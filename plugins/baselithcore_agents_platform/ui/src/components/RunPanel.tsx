import { useState } from 'react';
import { api } from '../lib/api';
import type { AgentBlueprint, AgentCapability, AgentRunResult } from '../lib/types';

const NEEDS_CODE: AgentCapability[] = ['fix', 'test', 'refactor', 'explain'];

interface RunPanelProps {
  blueprint: AgentBlueprint;
}

/** Inline runner: pick an in-scope capability, supply a task, view the result. */
export function RunPanel({ blueprint }: RunPanelProps) {
  const caps = blueprint.scope.capabilities;
  const [capability, setCapability] = useState<AgentCapability>(caps[0]);
  const [task, setTask] = useState('');
  const [code, setCode] = useState('');
  const [result, setResult] = useState<AgentRunResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function run() {
    setBusy(true);
    setError(null);
    setResult(null);
    try {
      setResult(await api.runAgent(blueprint.id, capability, task, code));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap gap-2">
        {caps.map((cap) => (
          <button
            key={cap}
            onClick={() => setCapability(cap)}
            className={[
              'rounded-lg px-3 py-1.5 text-xs font-medium transition-colors',
              capability === cap
                ? 'bg-iris/20 text-slate-100 shadow-glow'
                : 'bg-ink-700/60 text-slate-400 hover:text-slate-200',
            ].join(' ')}
          >
            {cap}
          </button>
        ))}
      </div>
      <textarea
        value={task}
        onChange={(e) => setTask(e.target.value)}
        rows={3}
        placeholder="Describe the task or paste the error message…"
        className="w-full rounded-xl border border-ink-600/60 bg-ink-900/60 p-3 text-sm text-slate-100 outline-none focus:border-iris/50"
      />
      {NEEDS_CODE.includes(capability) && (
        <textarea
          value={code}
          onChange={(e) => setCode(e.target.value)}
          rows={5}
          placeholder="Source code context…"
          className="w-full rounded-xl border border-ink-600/60 bg-ink-900/60 p-3 font-mono text-xs text-slate-100 outline-none focus:border-iris/50"
        />
      )}
      <button
        onClick={run}
        disabled={busy || !task.trim()}
        className="rounded-lg bg-gradient-to-r from-iris to-cyan px-4 py-2 text-sm font-semibold text-ink-900 disabled:opacity-40"
      >
        {busy ? 'Running…' : `Run ${capability}`}
      </button>

      {error && <p className="text-sm text-rose-400">{error}</p>}
      {result && <RunResult result={result} />}
    </div>
  );
}

const STATUS_TINT: Record<string, string> = {
  succeeded: 'text-emerald-300',
  failed: 'text-rose-400',
  rejected: 'text-amber-300',
};

function RunResult({ result }: { result: AgentRunResult }) {
  return (
    <div className="rounded-xl border border-ink-600/60 bg-ink-900/50 p-4">
      <div className="mb-2 flex items-center gap-3 text-xs">
        <span className={`font-semibold ${STATUS_TINT[result.status] ?? 'text-slate-300'}`}>
          {result.status}
        </span>
        <span className="text-slate-500">{result.iterations} iteration(s)</span>
      </div>
      {result.error && <p className="mb-2 text-sm text-rose-400">{result.error}</p>}
      {result.output && (
        <pre className="max-h-72 overflow-auto rounded-lg bg-black/40 p-3 font-mono text-xs text-slate-200">
          {result.output}
        </pre>
      )}
      {result.citations.length > 0 && (
        <div className="mt-3">
          <p className="mb-1 text-[11px] uppercase tracking-wide text-slate-500">Grounded in</p>
          <div className="flex flex-wrap gap-1.5">
            {result.citations.map((c) => (
              <span
                key={c.namespace}
                className="rounded bg-ink-700/70 px-1.5 py-0.5 font-mono text-[10px] text-cyan"
              >
                {c.namespace}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
