'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  Activity,
  FileText,
  Gauge,
  ListChecks,
  LockKeyhole,
  Radar,
  ScrollText,
  Settings as SettingsIcon,
  Shield,
  type LucideIcon,
} from 'lucide-react';
import { useTranslations } from 'next-intl';
import { cn } from '@/lib/cn';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from './ui/tooltip';

type NavKey = 'workspace' | 'scan' | 'documents' | 'policies' | 'audit' | 'settings';

interface NavItem {
  key: NavKey;
  href: string;
  icon: LucideIcon;
}

const ITEMS: NavItem[] = [
  { key: 'workspace', href: '/', icon: Gauge },
  { key: 'scan', href: '/scan', icon: Radar },
  { key: 'documents', href: '/documents', icon: FileText },
  { key: 'policies', href: '/policies', icon: ListChecks },
  { key: 'audit', href: '/audit', icon: ScrollText },
  { key: 'settings', href: '/settings', icon: SettingsIcon },
];

export function Sidebar() {
  const pathname = usePathname();
  const t = useTranslations('nav');
  const tCommon = useTranslations('common');

  return (
    <TooltipProvider delayDuration={120}>
      <nav className="h-screen w-[68px] shrink-0 border-r border-border bg-bg-panel-soft flex flex-col xl:w-[244px]">
        <div className="h-14 px-3 xl:px-4 border-b border-border flex items-center justify-center xl:justify-start gap-3">
          <div className="relative">
            <div className="w-8 h-8 rounded-md border border-border-strong bg-bg-panel-elev flex items-center justify-center">
              <Shield className="w-4.5 h-4.5 text-status-info" />
            </div>
          </div>
          <div className="hidden min-w-0 xl:block">
            <div className="text-sm font-semibold tracking-tight">{tCommon('appName')}</div>
            <div className="text-[10px] uppercase tracking-[0.18em] text-text-muted">
              {tCommon('tagline')}
            </div>
          </div>
        </div>

        <div className="px-2 xl:px-3 py-4 flex-1 overflow-y-auto">
          <div className="hidden px-2.5 mb-2 text-[10px] font-semibold uppercase tracking-[0.18em] text-text-muted xl:block">
            {t('console')}
          </div>
          <div className="space-y-1">
            {ITEMS.map((item) => (
              <NavLink
                key={item.href}
                item={item}
                label={t(`items.${item.key}.label`)}
                description={t(`items.${item.key}.description`)}
                active={pathname === item.href}
              />
            ))}
          </div>
        </div>

        <div className="hidden p-3 xl:block">
          <div className="rounded-lg border border-border surface-elev p-3 shadow-inner-soft">
            <div className="flex items-center gap-2 text-xs font-semibold text-text-primary">
              <LockKeyhole size={14} className="text-status-success" />
              {t('secureMode')}
            </div>
            <ul className="mt-3 space-y-1.5 text-[11px] text-text-muted">
              <Stat label={t('stats.rbac')} value={t('stats.rbacValue')} tone="success" />
              <Stat
                label={t('stats.auditChain')}
                value={t('stats.auditChainValue')}
                tone="success"
              />
              <Stat label={t('stats.egress')} value={t('stats.egressValue')} tone="muted" />
            </ul>
            <div className="mt-3 flex items-center gap-1.5 border-t border-border pt-3 text-[10px] text-text-muted">
              <Activity size={11} className="text-status-success" />
              {t('heartbeat')}
            </div>
          </div>
        </div>
      </nav>
    </TooltipProvider>
  );
}

function NavLink({
  item,
  label,
  description,
  active,
}: {
  item: NavItem;
  label: string;
  description: string;
  active: boolean;
}) {
  const Icon = item.icon;
  const inner = (
    <Link
      href={item.href}
      aria-label={label}
      aria-current={active ? 'page' : undefined}
      className={cn(
        'group relative flex items-center justify-center xl:justify-start gap-3 rounded-lg px-2 xl:px-2.5 py-2 transition-colors duration-150 ease-smooth',
        active
          ? 'bg-bg-panel-elev text-text-primary'
          : 'text-text-secondary hover:bg-bg-panel hover:text-text-primary'
      )}
    >
      {active && (
        <span className="absolute -left-2 top-1/2 -translate-y-1/2 h-5 w-0.5 rounded-full bg-status-info shadow-[0_0_10px_rgba(47,123,255,0.7)] hidden xl:block" />
      )}
      <span
        className={cn(
          'flex h-8 w-8 shrink-0 items-center justify-center rounded-md border transition-all duration-150',
          active
            ? 'border-status-info/40 bg-status-info/15 text-status-info shadow-[inset_0_0_0_1px_rgba(47,123,255,0.2)]'
            : 'border-border bg-bg-canvas text-text-muted group-hover:text-text-primary group-hover:border-border-strong'
        )}
      >
        <Icon size={15} />
      </span>
      <span className="hidden min-w-0 xl:block">
        <span className="block text-[13px] font-medium leading-tight">{label}</span>
        <span className="block truncate text-[10px] text-text-muted">{description}</span>
      </span>
    </Link>
  );

  return (
    <Tooltip>
      <TooltipTrigger asChild>{inner}</TooltipTrigger>
      <TooltipContent side="right" className="xl:hidden">
        {label}
      </TooltipContent>
    </Tooltip>
  );
}

function Stat({ label, value, tone }: { label: string; value: string; tone: 'success' | 'muted' }) {
  return (
    <li className="flex items-center justify-between">
      <span>{label}</span>
      <span className={tone === 'success' ? 'text-status-success' : 'text-text-secondary'}>
        {value}
      </span>
    </li>
  );
}
