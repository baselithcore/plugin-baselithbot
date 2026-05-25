export function EmptyState({ onPick }: { onPick: (t: string) => void }) {
  const examples = ['https://api.example.com', 'example.com', '10.0.0.1'];
  return (
    <div className="absolute inset-0 grid place-items-center p-6">
      <div className="max-w-md text-center">
        <div
          className="mx-auto h-16 w-16 rounded-full border border-accent-neon/40 bg-accent-neon/5"
          style={{ boxShadow: '0 0 36px rgba(0,255,209,0.18)' }}
          aria-hidden
        />
        <h2 className="mt-5 font-display text-lg text-text-primary">No graph loaded</h2>
        <p className="mt-2 text-sm text-text-muted">
          Enter a target above to explore its attack surface. Nodes are rendered with severity rings
          and edges colored by relation.
        </p>
        <div className="mt-5 flex flex-wrap justify-center gap-2">
          {examples.map((e) => (
            <button
              key={e}
              type="button"
              onClick={() => onPick(e)}
              className="rounded border border-bg-line bg-bg-elevated px-3 py-1.5 font-display text-xs text-text-muted hover:border-accent-neon/40 hover:text-accent-neon"
            >
              {e}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

export function NoResultsState({ target, onClear }: { target: string; onClear: () => void }) {
  return (
    <div className="absolute inset-0 grid place-items-center p-6">
      <div className="max-w-md text-center">
        <div
          className="mx-auto h-14 w-14 rounded-full border border-bg-line bg-bg-elevated"
          aria-hidden
        />
        <h2 className="mt-5 font-display text-base text-text-primary">No graph data</h2>
        <p className="mt-2 text-sm text-text-muted">
          The graph store has no nodes for{' '}
          <code className="rounded bg-bg-elevated px-1.5 py-0.5 font-display text-text-primary">
            {target}
          </code>
          . Run a scan first or check the target value.
        </p>
        <button
          type="button"
          onClick={onClear}
          className="mt-5 rounded border border-bg-line bg-bg-elevated px-3 py-1.5 font-display text-xs text-text-muted hover:text-text-primary"
        >
          clear
        </button>
      </div>
    </div>
  );
}
