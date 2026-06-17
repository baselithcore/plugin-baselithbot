// Long-term memory panel: the salient facts the twin has learned, sorted by
// salience, with their tags and originating contact.

import { useTranslation } from 'react-i18next';
import { Brain } from 'lucide-react';
import type { SalientFact } from '../api/types';
import { Badge, Card } from './ui';

export function MemoryPanel({ facts }: { facts: SalientFact[] }) {
  const { t } = useTranslation();
  const sorted = [...facts].sort((a, b) => b.salience - a.salience);
  return (
    <Card title={t('memory.title')}>
      {sorted.length === 0 ? (
        <p className="py-6 text-center text-sm text-white/30">{t('memory.empty')}</p>
      ) : (
        <ul className="max-h-72 space-y-2 overflow-y-auto pr-1">
          {sorted.map((f) => (
            <li key={f.id} className="rounded-xl border border-white/5 bg-white/[0.02] p-3">
              <div className="flex items-start gap-2">
                <Brain className="mt-0.5 h-4 w-4 shrink-0 text-accent-400" />
                <div className="min-w-0 flex-1">
                  <p className="text-sm text-white/80">{f.text}</p>
                  <div className="mt-1.5 flex flex-wrap items-center gap-1.5">
                    <Badge tone="brand">
                      {t('memory.salience')} {(f.salience * 100).toFixed(0)}%
                    </Badge>
                    <span className="font-mono text-[10px] text-white/30">{f.contact_id}</span>
                    {f.tags.map((tag) => (
                      <Badge key={tag}>#{tag}</Badge>
                    ))}
                  </div>
                </div>
              </div>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}
