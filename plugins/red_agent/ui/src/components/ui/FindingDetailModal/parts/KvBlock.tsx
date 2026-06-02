export function KvBlock({
  data,
  empty,
  raw,
}: {
  data: Record<string, unknown>;
  empty: string;
  raw?: boolean;
}) {
  if (Object.keys(data).length === 0) {
    return <div className="grid place-items-center py-12 text-sm text-text-muted">{empty}</div>;
  }
  if (raw) {
    return (
      <pre className="overflow-x-auto rounded border border-bg-line bg-bg-base px-3 py-2.5 font-mono text-xs leading-relaxed text-text-secondary">
        {JSON.stringify(data, null, 2)}
      </pre>
    );
  }
  return (
    <dl className="space-y-2">
      {Object.entries(data).map(([k, v]) => (
        <div
          key={k}
          className="grid gap-1 rounded border border-bg-line/60 bg-bg-base/50 px-3 py-2 sm:grid-cols-[200px_1fr]"
        >
          <dt className="text-2xs font-mono uppercase tracking-wider text-text-muted">{k}</dt>
          <dd className="font-mono text-xs text-text-primary break-words">
            {typeof v === 'object' && v !== null ? (
              <pre className="whitespace-pre-wrap">{JSON.stringify(v, null, 2)}</pre>
            ) : (
              String(v)
            )}
          </dd>
        </div>
      ))}
    </dl>
  );
}
