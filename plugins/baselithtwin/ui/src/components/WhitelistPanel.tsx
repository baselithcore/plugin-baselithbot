// Whitelist management: contacts here are auto-answered (subject to the autonomy
// policy and confidence/rate gates); everyone else is queued for approval.

import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Plus, Trash2 } from 'lucide-react';
import type { WhitelistEntry } from '../api/types';
import { Button, Card } from './ui';

export function WhitelistPanel({
  entries,
  onAdd,
  onRemove,
}: {
  entries: WhitelistEntry[];
  onAdd: (id: string, name?: string) => void;
  onRemove: (id: string) => void;
}) {
  const { t } = useTranslation();
  const [id, setId] = useState('');
  const [name, setName] = useState('');

  const submit = () => {
    if (!id.trim()) return;
    onAdd(id.trim(), name.trim() || undefined);
    setId('');
    setName('');
  };

  return (
    <Card title={t('whitelist.title')}>
      <div className="mb-3 flex flex-col gap-2 sm:flex-row">
        <input
          value={id}
          onChange={(e) => setId(e.target.value)}
          placeholder={t('whitelist.placeholder')}
          className="flex-1 rounded-lg border border-white/10 bg-ink-900/60 px-3 py-1.5 text-sm text-white placeholder:text-white/30 focus:border-brand-500 focus:outline-none"
        />
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder={t('whitelist.name')}
          className="w-full rounded-lg border border-white/10 bg-ink-900/60 px-3 py-1.5 text-sm text-white placeholder:text-white/30 focus:border-brand-500 focus:outline-none sm:w-40"
        />
        <Button variant="primary" onClick={submit}>
          <Plus className="mr-1 inline h-3.5 w-3.5" />
          {t('whitelist.add')}
        </Button>
      </div>
      {entries.length === 0 ? (
        <p className="py-4 text-center text-sm text-white/30">{t('whitelist.empty')}</p>
      ) : (
        <ul className="space-y-1.5">
          {entries.map((e) => (
            <li
              key={e.contact_id}
              className="flex items-center justify-between rounded-lg border border-white/5 bg-white/[0.02] px-3 py-2"
            >
              <div>
                {e.display_name && <span className="text-sm text-white/90">{e.display_name} </span>}
                <span className="font-mono text-xs text-white/40">{e.contact_id}</span>
              </div>
              <button
                onClick={() => onRemove(e.contact_id)}
                aria-label={t('whitelist.remove')}
                className="text-white/40 transition-colors hover:text-rose-400"
              >
                <Trash2 className="h-4 w-4" />
              </button>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}
