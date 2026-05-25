import { useState } from 'react';
import { Check, Copy } from 'lucide-react';

interface Props {
  sql: string;
}

const KEYWORDS = new Set([
  'SELECT',
  'FROM',
  'WHERE',
  'JOIN',
  'LEFT',
  'RIGHT',
  'INNER',
  'OUTER',
  'ON',
  'GROUP',
  'BY',
  'ORDER',
  'LIMIT',
  'OFFSET',
  'HAVING',
  'AS',
  'AND',
  'OR',
  'NOT',
  'IN',
  'EXISTS',
  'UNION',
  'ALL',
  'DISTINCT',
  'WITH',
  'CASE',
  'WHEN',
  'THEN',
  'ELSE',
  'END',
  'NULL',
  'IS',
  'ASC',
  'DESC',
  'BETWEEN',
  'LIKE',
  'ILIKE',
]);

interface Token {
  text: string;
  kind: 'keyword' | 'comment' | 'string' | 'number' | 'plain';
}

function tokenize(sql: string): Token[] {
  const out: Token[] = [];
  let i = 0;
  const n = sql.length;
  while (i < n) {
    const ch = sql[i]!;
    if (ch === '-' && sql[i + 1] === '-') {
      const end = sql.indexOf('\n', i);
      const stop = end === -1 ? n : end;
      out.push({ text: sql.slice(i, stop), kind: 'comment' });
      i = stop;
      continue;
    }
    if (ch === '/' && sql[i + 1] === '*') {
      const end = sql.indexOf('*/', i + 2);
      const stop = end === -1 ? n : end + 2;
      out.push({ text: sql.slice(i, stop), kind: 'comment' });
      i = stop;
      continue;
    }
    if (ch === "'" || ch === '"') {
      const quote = ch;
      let j = i + 1;
      while (j < n && sql[j] !== quote) j++;
      out.push({ text: sql.slice(i, Math.min(j + 1, n)), kind: 'string' });
      i = j + 1;
      continue;
    }
    if (/\d/.test(ch)) {
      let j = i;
      while (j < n && /[\d.]/.test(sql[j]!)) j++;
      out.push({ text: sql.slice(i, j), kind: 'number' });
      i = j;
      continue;
    }
    if (/[A-Za-z_]/.test(ch)) {
      let j = i;
      while (j < n && /[A-Za-z0-9_]/.test(sql[j]!)) j++;
      const word = sql.slice(i, j);
      out.push({
        text: word,
        kind: KEYWORDS.has(word.toUpperCase()) ? 'keyword' : 'plain',
      });
      i = j;
      continue;
    }
    out.push({ text: ch, kind: 'plain' });
    i++;
  }
  return out;
}

const COLOR: Record<Token['kind'], string> = {
  keyword: 'text-violet-400 font-semibold',
  comment: 'text-text-dim italic',
  string: 'text-emerald-400',
  number: 'text-amber-400',
  plain: 'text-text',
};

export function SqlBlock({ sql }: Props) {
  const tokens = tokenize(sql);
  const [copied, setCopied] = useState(false);

  const onCopy = () => {
    navigator.clipboard.writeText(sql);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1100);
  };

  return (
    <div className="relative group/sql">
      <pre className="text-xs bg-surface-2/70 p-3 pr-10 overflow-auto font-mono whitespace-pre-wrap">
        {tokens.map((t, i) => (
          <span key={i} className={COLOR[t.kind]}>
            {t.text}
          </span>
        ))}
      </pre>
      <button
        type="button"
        onClick={onCopy}
        aria-label={copied ? 'Copied' : 'Copy SQL'}
        title={copied ? 'Copied' : 'Copy SQL'}
        className="absolute top-2 right-2 inline-flex items-center justify-center w-7 h-7 rounded-md text-text-dim opacity-0 group-hover/sql:opacity-100 focus-visible:opacity-100 transition-opacity hover:text-text hover:bg-surface-3"
      >
        {copied ? (
          <Check key="check" className="w-3.5 h-3.5 text-success tick-in" strokeWidth={2.5} />
        ) : (
          <Copy className="w-3.5 h-3.5" />
        )}
      </button>
    </div>
  );
}
