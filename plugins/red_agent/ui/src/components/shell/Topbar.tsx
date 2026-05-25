import { NavLink, useNavigate } from 'react-router-dom';
import { useEffect, useRef, useState, KeyboardEvent } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Icon } from '../ui/Icon';
import { Button } from '../ui/Button';
import { MenuDivider, MenuHeader, MenuItem, Popover } from '../ui/Popover';
import { api, type ScanRow } from '../../lib/api';

const ENVIRONMENTS = ['production', 'staging', 'development'];
const TENANTS = [
  { id: 'all', label: 'all targets' },
  { id: 'default', label: 'default' },
];

const MOBILE_NAV = [
  { to: '/', label: 'Overview', icon: <Icon.Dashboard size={15} />, end: true },
  { to: '/targets', label: 'Targets', icon: <Icon.Target size={15} /> },
  { to: '/scans', label: 'Scans', icon: <Icon.Scans size={15} /> },
  { to: '/findings', label: 'Findings', icon: <Icon.Findings size={15} /> },
  { to: '/graph', label: 'Graph', icon: <Icon.Graph size={15} /> },
];

export function Topbar() {
  const nav = useNavigate();
  const [q, setQ] = useState('');
  const [env, setEnv] = useState<string>(
    () => localStorage.getItem('red_agent.env') ?? 'production'
  );
  const [tenant, setTenant] = useState<string>(
    () => localStorage.getItem('red_agent.tenant') ?? 'all'
  );

  useEffect(() => {
    localStorage.setItem('red_agent.env', env);
  }, [env]);
  useEffect(() => {
    localStorage.setItem('red_agent.tenant', tenant);
  }, [tenant]);

  const searchRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    function onGlobalKey(e: globalThis.KeyboardEvent) {
      const meta = e.metaKey || e.ctrlKey;
      if (meta && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        searchRef.current?.focus();
        searchRef.current?.select();
      }
    }
    window.addEventListener('keydown', onGlobalKey);
    return () => window.removeEventListener('keydown', onGlobalKey);
  }, []);

  function onKey(e: KeyboardEvent<HTMLInputElement>) {
    if (e.key === 'Enter' && q.trim()) {
      nav(`/findings?target=${encodeURIComponent(q.trim())}`);
    } else if (e.key === 'Escape') {
      setQ('');
      e.currentTarget.blur();
    }
  }

  const { data: recent = [] } = useQuery<ScanRow[]>({
    queryKey: ['topbar.recent'],
    queryFn: () => api.listScans({ limit: 6 }),
    refetchInterval: 15000,
  });

  const tenantLabel = TENANTS.find((t) => t.id === tenant)?.label ?? tenant;

  const notifications = recent.filter(
    (s) => s.status === 'awaiting_approval' || s.status === 'failed'
  );

  return (
    <header className="sticky top-0 z-20 flex min-h-14 flex-wrap items-center gap-3 border-b border-bg-line bg-bg-base/85 px-4 py-2 backdrop-blur-xl sm:px-6">
      <Popover
        align="left"
        width={260}
        trigger={
          <button
            type="button"
            className="grid h-9 w-9 place-items-center rounded-md border border-bg-line bg-bg-elevated text-text-secondary transition-colors hover:border-bg-line-strong hover:text-text-primary lg:hidden"
            title="Navigation"
            aria-label="Navigation"
          >
            <Icon.Sliders size={15} />
          </button>
        }
      >
        {(close) => (
          <div className="py-2">
            <MenuHeader>Red Agent</MenuHeader>
            <div className="px-2">
              {MOBILE_NAV.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  end={item.end}
                  onClick={close}
                  className={({ isActive }) =>
                    `mb-1 flex items-center gap-2 rounded-md px-3 py-2 text-sm transition-colors ${
                      isActive
                        ? 'bg-brand/10 text-brand'
                        : 'text-text-secondary hover:bg-bg-overlay hover:text-text-primary'
                    }`
                  }
                >
                  {item.icon}
                  {item.label}
                </NavLink>
              ))}
            </div>
            <MenuDivider />
            <MenuItem
              icon={<Icon.Plus size={12} />}
              label="New operation"
              onSelect={() => {
                nav('/scans/new');
                close();
              }}
            />
            <MenuItem
              icon={<Icon.Shield size={12} />}
              label="Scope & policy"
              onSelect={() => {
                nav('/settings/scope');
                close();
              }}
            />
          </div>
        )}
      </Popover>

      {/* Left cluster: env badge + project picker */}
      <div className="flex items-center gap-2">
        <Popover
          align="left"
          width={200}
          trigger={
            <button
              type="button"
              className="inline-flex items-center gap-1.5 rounded-md border border-brand/30 bg-brand/10 px-2.5 py-1 text-xs font-medium text-brand transition-colors hover:bg-brand/15"
              title="Environment"
            >
              <Icon.Layers size={12} />
              <span className="font-mono">{env}</span>
              <Icon.ChevronDown size={11} className="text-brand/70" />
            </button>
          }
        >
          {(close) => (
            <div className="py-1">
              <MenuHeader>Environment</MenuHeader>
              {ENVIRONMENTS.map((e) => (
                <MenuItem
                  key={e}
                  icon={<Icon.Layers size={12} />}
                  label={<span className="font-mono">{e}</span>}
                  onSelect={() => {
                    setEnv(e);
                    close();
                  }}
                />
              ))}
            </div>
          )}
        </Popover>

        <Popover
          align="left"
          width={220}
          trigger={
            <button
              type="button"
              className="inline-flex items-center gap-1.5 rounded-md border border-bg-line bg-bg-elevated px-2.5 py-1 text-xs text-text-secondary transition-colors hover:border-bg-line-strong hover:text-text-primary"
              title="Project / tenant"
            >
              <Icon.Folder size={12} />
              <span className="font-mono">{tenantLabel}</span>
              <Icon.ChevronDown size={11} className="text-text-muted" />
            </button>
          }
        >
          {(close) => (
            <div className="py-1">
              <MenuHeader>Tenant</MenuHeader>
              {TENANTS.map((t) => (
                <MenuItem
                  key={t.id}
                  icon={<Icon.Folder size={12} />}
                  label={<span className="font-mono">{t.label}</span>}
                  onSelect={() => {
                    setTenant(t.id);
                    close();
                  }}
                />
              ))}
            </div>
          )}
        </Popover>
      </div>

      {/* Centre: search */}
      <div className="order-3 flex w-full items-center justify-center lg:order-none lg:w-auto lg:flex-1 lg:px-4">
        <div className="relative w-full max-w-xl">
          <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-text-muted">
            <Icon.Search size={14} />
          </span>
          <input
            ref={searchRef}
            value={q}
            onChange={(e) => setQ(e.target.value)}
            onKeyDown={onKey}
            placeholder="Search findings, scans, targets, CVE…"
            className="ra-input pl-9 pr-14 h-9"
            aria-label="Global search"
          />
          <span className="pointer-events-none absolute right-2.5 top-1/2 -translate-y-1/2 rounded border border-bg-line px-1.5 py-0.5 text-2xs font-mono text-text-muted">
            ⌘K
          </span>
        </div>
      </div>

      {/* Right cluster */}
      <div className="ml-auto flex items-center gap-1">
        <button
          type="button"
          onClick={() => nav('/scans/new')}
          title="Ask Red AI — natural-language assistant"
          className="group inline-flex h-9 items-center gap-2 rounded-md border border-bg-line bg-bg-overlay px-3 text-sm font-medium text-text-primary transition-colors hover:border-brand/40 hover:bg-bg-hover"
        >
          <span className="grid h-5 w-5 place-items-center rounded bg-brand/10 text-brand">
            <Icon.Sparkles size={12} />
          </span>
          <span className="hidden md:inline">Ask Red AI</span>
        </button>

        <Popover
          width={320}
          trigger={
            <Button variant="ghost" size="sm" title="Activity">
              <Icon.Activity size={15} />
            </Button>
          }
        >
          {(close) => (
            <div className="py-1">
              <MenuHeader>Recent activity</MenuHeader>
              {recent.length === 0 ? (
                <div className="px-3 py-4 text-xs text-text-muted">No scans yet.</div>
              ) : (
                recent.map((s) => (
                  <MenuItem
                    key={s.id}
                    icon={<Icon.Scans size={12} />}
                    label={
                      <span className="font-mono text-xs">
                        {s.target_value} · {s.status}
                      </span>
                    }
                    description={s.scanners.join(', ')}
                    onSelect={() => {
                      nav(`/scans/${s.id}`);
                      close();
                    }}
                  />
                ))
              )}
              <MenuDivider />
              <MenuItem
                icon={<Icon.ArrowRight size={12} />}
                label="View all scans"
                onSelect={() => {
                  nav('/scans');
                  close();
                }}
              />
            </div>
          )}
        </Popover>

        <Popover
          width={320}
          trigger={
            <Button variant="ghost" size="sm" title="Notifications" className="relative">
              <Icon.Bell size={15} />
              {notifications.length > 0 && (
                <span className="absolute right-1 top-1 grid h-4 min-w-4 place-items-center rounded-full bg-sev-critical px-1 text-[9px] font-mono font-semibold text-white ring-2 ring-bg-base">
                  {notifications.length}
                </span>
              )}
            </Button>
          }
        >
          {(close) => (
            <div className="py-1">
              <MenuHeader>Notifications</MenuHeader>
              {notifications.length === 0 ? (
                <div className="px-3 py-4 text-xs text-text-muted">All clear.</div>
              ) : (
                notifications.map((s) => (
                  <MenuItem
                    key={s.id}
                    icon={
                      s.status === 'awaiting_approval' ? (
                        <Icon.Shield size={12} />
                      ) : (
                        <Icon.X size={12} />
                      )
                    }
                    label={
                      <span className="font-mono text-xs">
                        {s.status === 'awaiting_approval' ? 'HITL approval needed' : 'Scan failed'}
                      </span>
                    }
                    description={s.target_value}
                    onSelect={() => {
                      nav(`/scans/${s.id}`);
                      close();
                    }}
                  />
                ))
              )}
            </div>
          )}
        </Popover>

        <Popover
          width={240}
          trigger={
            <Button variant="ghost" size="sm" title="Help">
              <Icon.Help size={15} />
            </Button>
          }
        >
          <div className="py-1">
            <MenuHeader>Help</MenuHeader>
            <MenuItem
              icon={<Icon.Help size={12} />}
              label="Documentation"
              href="https://github.com/baselithcore"
            />
            <MenuItem
              icon={<Icon.Bug size={12} />}
              label="Report an issue"
              href="https://github.com/baselithcore/baselithcore-prod/issues"
            />
            <MenuItem icon={<Icon.Activity size={12} />} label="API reference" href="/docs" />
            <MenuDivider />
            <MenuItem icon={<Icon.Shield size={12} />} label="Red Agent v0.1.0" disabled />
          </div>
        </Popover>

        <Popover
          width={220}
          trigger={
            <button
              type="button"
              className="ml-2 flex items-center gap-2 border-l border-bg-line pl-3"
              title="Account"
            >
              <div className="grid h-7 w-7 place-items-center rounded-full bg-gradient-brand text-xs font-display font-semibold text-text-primary ring-1 ring-bg-line">
                OP
              </div>
              <div className="hidden text-xs leading-tight md:block">
                <div className="font-medium text-text-primary">Operator</div>
                <div className="font-mono text-text-muted">red-agent</div>
              </div>
            </button>
          }
        >
          {(close) => (
            <div className="py-1">
              <MenuHeader>Account</MenuHeader>
              <MenuItem
                icon={<Icon.Settings size={12} />}
                label="Scope & policy"
                onSelect={() => {
                  nav('/settings/scope');
                  close();
                }}
              />
              <MenuItem
                icon={<Icon.Shield size={12} />}
                label="Pending approvals"
                onSelect={() => {
                  nav('/scans?status_filter=awaiting_approval');
                  close();
                }}
              />
              <MenuDivider />
              <MenuItem
                icon={<Icon.X size={12} />}
                label="Sign out"
                danger
                onSelect={() => {
                  localStorage.removeItem('red_agent.token');
                  window.location.reload();
                }}
              />
            </div>
          )}
        </Popover>
      </div>
    </header>
  );
}
