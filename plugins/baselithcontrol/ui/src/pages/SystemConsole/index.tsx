import { useState } from 'react';
import { motion } from 'motion/react';
import { useTranslation } from 'react-i18next';
import { Activity, Server, Wrench, DollarSign } from 'lucide-react';
import { pageVariants } from '@/lib/motion';
import { DiagnosticsPanel } from './DiagnosticsPanel';
import { InfraPanel } from './InfraPanel';
import { DevToolsPanel } from './DevToolsPanel';
import { CostsPanel } from './CostsPanel';

type Sub = 'diagnostics' | 'infra' | 'devtools' | 'costs';

const SUBS: { id: Sub; icon: typeof Activity; label: string }[] = [
  { id: 'diagnostics', icon: Activity, label: 'console.tab_diagnostics' },
  { id: 'infra', icon: Server, label: 'console.tab_infra' },
  { id: 'devtools', icon: Wrench, label: 'console.tab_devtools' },
  { id: 'costs', icon: DollarSign, label: 'console.tab_costs' },
];

export function SystemConsole() {
  const { t } = useTranslation();
  const [sub, setSub] = useState<Sub>('diagnostics');

  return (
    <motion.div
      variants={pageVariants}
      initial="hidden"
      animate="show"
      exit="exit"
      className="space-y-6"
    >
      <div className="flex flex-col gap-4 border-b brd pb-5 sm:flex-row sm:items-end sm:justify-between">
        <div className="space-y-1">
          <h1 className="font-display text-[1.6rem] font-bold leading-tight tracking-tight t-primary">
            {t('console.title')}
          </h1>
          <p className="text-[13px] t-dim">{t('console.subtitle')}</p>
        </div>
        <nav className="flex items-center gap-1 rounded-xl border brd bg-[var(--surface-inset)] p-1">
          {SUBS.map(({ id, icon: Icon, label }) => (
            <button
              key={id}
              type="button"
              onClick={() => setSub(id)}
              aria-current={sub === id ? 'page' : undefined}
              className={`flex items-center gap-2 rounded-lg px-3.5 py-2 text-[13px] font-semibold transition ${
                sub === id
                  ? 'bg-[var(--accent-soft)] t-accent'
                  : 't-dim hover:bg-[var(--surface-2)]'
              }`}
            >
              <Icon className="h-4 w-4" />
              <span className="hidden sm:block">{t(label)}</span>
            </button>
          ))}
        </nav>
      </div>

      {sub === 'diagnostics' && <DiagnosticsPanel />}
      {sub === 'infra' && <InfraPanel />}
      {sub === 'devtools' && <DevToolsPanel />}
      {sub === 'costs' && <CostsPanel />}
    </motion.div>
  );
}
