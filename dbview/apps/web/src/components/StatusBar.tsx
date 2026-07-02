import { Activity, Cpu, Database, Globe } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { api } from '../lib/api.js';
import { useAppStore } from '../store/app.js';

export function StatusBar() {
  const connId = useAppStore((s) => s.activeConnectionId);
  const provider = useAppStore((s) => s.provider);
  const conn = useQuery({
    queryKey: ['connections'],
    queryFn: api.listConnections,
    select: (list) => list.find((c) => c.id === connId),
    enabled: !!connId,
  });
  const isConnected = !!connId && !!conn.data;

  return (
    <footer
      className="flex items-center justify-between h-7 px-3 text-[11px] font-mono border-t gap-4"
      style={{
        borderColor: 'rgb(var(--border-subtle))',
        background: 'rgb(var(--surface-elevated) / 0.86)',
        color: 'rgb(var(--text-muted))',
      }}
    >
      <div className="flex items-center gap-3 min-w-0">
        <span className="flex items-center gap-1.5">
          <Activity className={isConnected ? 'w-3 h-3 text-success' : 'w-3 h-3 text-text-dim'} />
          <span>{isConnected ? 'connected' : 'no connection'}</span>
        </span>
        {conn.data && (
          <>
            <span className="text-text-dim">·</span>
            <span className="flex items-center gap-1.5 min-w-0">
              <Database className="w-3 h-3" />
              <span>{conn.data.dialect}</span>
              <span className="text-text-dim">/</span>
              <span className="truncate">{conn.data.name}</span>
            </span>
          </>
        )}
      </div>
      <div className="flex items-center gap-3 shrink-0">
        <span className="flex items-center gap-1.5">
          <Cpu className="w-3 h-3" />
          <span>{provider}</span>
        </span>
        <span className="text-text-dim">·</span>
        <span className="flex items-center gap-1.5">
          <Globe className="w-3 h-3" />
          <span>v0.1.0</span>
        </span>
      </div>
    </footer>
  );
}
