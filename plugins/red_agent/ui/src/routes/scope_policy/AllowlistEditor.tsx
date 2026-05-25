import { useState } from 'react';
import { Button, EmptyState, Icon } from '../../components/ui';

export function AllowlistEditor({
  entries,
  onChange,
}: {
  entries: string[];
  onChange: (entries: string[]) => void;
}) {
  const [input, setInput] = useState('');
  const add = () => {
    const v = input.trim();
    if (!v) return;
    if (entries.includes(v)) {
      setInput('');
      return;
    }
    onChange([...entries, v]);
    setInput('');
  };
  return (
    <div className="space-y-3">
      <div className="flex gap-2">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') {
              e.preventDefault();
              add();
            }
          }}
          placeholder="example.com  ·  10.0.0.0/24  ·  https://api.example.com"
          className="ra-input flex-1"
        />
        <Button variant="secondary" size="sm" onClick={add} disabled={!input.trim()}>
          <Icon.Plus size={12} />
          Add
        </Button>
      </div>
      {entries.length === 0 ? (
        <EmptyState
          compact
          icon={<Icon.Target size={20} />}
          title="Allowlist empty"
          description="Add a domain, IP or CIDR to authorize scanning."
        />
      ) : (
        <ul className="divide-y divide-bg-line/60 rounded-md border border-bg-line bg-bg-elevated">
          {entries.map((e) => (
            <li
              key={e}
              className="flex items-center justify-between gap-3 px-3 py-2 hover:bg-bg-hover/50"
            >
              <span className="font-mono text-sm text-text-primary truncate">{e}</span>
              <button
                type="button"
                onClick={() => onChange(entries.filter((x) => x !== e))}
                className="grid h-7 w-7 place-items-center rounded text-text-muted transition-colors hover:bg-sev-critical/15 hover:text-sev-critical"
                aria-label={`Remove ${e}`}
                title="Remove"
              >
                <Icon.X size={12} />
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
