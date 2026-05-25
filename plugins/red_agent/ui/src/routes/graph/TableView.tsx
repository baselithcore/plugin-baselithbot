import { useMemo, useState } from 'react';
import { SeverityPill } from '../../components/SeverityPill';
import type { CyNode } from '../../lib/api';
import { severityRank } from './styles';

type Col = 'display' | 'label' | 'severity' | 'cvss' | 'id';
type Dir = 'asc' | 'desc';

export function TableView({ nodes }: { nodes: CyNode[] }) {
  const [sort, setSort] = useState<{ col: Col; dir: Dir }>({ col: 'severity', dir: 'desc' });

  const sorted = useMemo(() => {
    const list = [...nodes];
    list.sort((a, b) => {
      const av = pick(a, sort.col);
      const bv = pick(b, sort.col);
      if (av === bv) return 0;
      const cmp = av < bv ? -1 : 1;
      return sort.dir === 'asc' ? cmp : -cmp;
    });
    return list;
  }, [nodes, sort]);

  function header(col: Col, label: string) {
    const active = sort.col === col;
    return (
      <th
        scope="col"
        className="cursor-pointer select-none border-b border-bg-line px-3 py-2 hover:text-text-primary"
        onClick={() =>
          setSort((s) =>
            s.col === col ? { col, dir: s.dir === 'asc' ? 'desc' : 'asc' } : { col, dir: 'desc' }
          )
        }
        aria-sort={active ? (sort.dir === 'asc' ? 'ascending' : 'descending') : 'none'}
      >
        {label}
        {active && <span className="ml-1 text-accent-neon">{sort.dir === 'asc' ? '▲' : '▼'}</span>}
      </th>
    );
  }

  return (
    <div className="absolute inset-0 overflow-auto p-4">
      <table className="w-full border-separate border-spacing-0 font-display text-xs">
        <thead className="sticky top-0 bg-bg-elevated text-left text-text-muted">
          <tr>
            {header('display', 'Display')}
            {header('label', 'Type')}
            {header('severity', 'Severity')}
            {header('cvss', 'CVSS')}
            {header('id', 'ID')}
          </tr>
        </thead>
        <tbody>
          {sorted.map((n) => (
            <tr key={n.data.id} className="hover:bg-bg-overlay">
              <td className="truncate border-b border-bg-line/50 px-3 py-2 text-text-primary">
                {n.data.display || n.data.id}
              </td>
              <td className="border-b border-bg-line/50 px-3 py-2 text-text-muted">
                {n.data.label}
              </td>
              <td className="border-b border-bg-line/50 px-3 py-2">
                {n.data.severity ? <SeverityPill severity={n.data.severity} /> : '—'}
              </td>
              <td className="border-b border-bg-line/50 px-3 py-2 text-text-primary">
                {n.data.cvss !== null && n.data.cvss !== undefined
                  ? Number(n.data.cvss).toFixed(1)
                  : '—'}
              </td>
              <td className="truncate border-b border-bg-line/50 px-3 py-2 text-[11px] text-text-muted">
                {n.data.id}
              </td>
            </tr>
          ))}
          {sorted.length === 0 && (
            <tr>
              <td colSpan={5} className="px-3 py-8 text-center text-text-muted">
                No rows.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}

function pick(n: CyNode, col: Col): string | number {
  switch (col) {
    case 'display':
      return (n.data.display || n.data.id).toLowerCase();
    case 'label':
      return n.data.label.toLowerCase();
    case 'severity':
      return severityRank(n.data.severity);
    case 'cvss':
      return n.data.cvss ?? -1;
    case 'id':
      return n.data.id.toLowerCase();
  }
}
