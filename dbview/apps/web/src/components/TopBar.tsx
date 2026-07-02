import { Activity, Command, Database, History, Moon, Settings, Sun } from 'lucide-react';
import { AnimatePresence, motion } from 'framer-motion';
import { useQuery } from '@tanstack/react-query';
import { useAppStore } from '../store/app.js';
import { api } from '../lib/api.js';
import { UserMenu } from './UserMenu.js';
import { HelpMenu } from './tour/HelpMenu.js';

export function TopBar() {
  const theme = useAppStore((s) => s.theme);
  const connId = useAppStore((s) => s.activeConnectionId);
  const toggleTheme = useAppStore((s) => s.toggleTheme);
  const setCommandOpen = useAppStore((s) => s.setCommandOpen);
  const setSettingsOpen = useAppStore((s) => s.setSettingsOpen);
  const setHistoryOpen = useAppStore((s) => s.setHistoryOpen);
  const activeConnection = useQuery({
    queryKey: ['connections'],
    queryFn: api.listConnections,
    select: (list) => list.find((c) => c.id === connId),
    enabled: !!connId,
  });
  const isConnected = !!activeConnection.data;

  return (
    <header
      className="flex items-center justify-between h-12 px-3 md:px-4 border-b shrink-0 backdrop-blur-xl gap-3"
      style={{
        borderColor: 'rgb(var(--border-subtle))',
        background: 'rgb(var(--surface-elevated) / 0.9)',
      }}
    >
      <div className="flex items-center gap-2.5 min-w-0">
        <div
          className="relative w-7 h-7 rounded-md flex items-center justify-center shrink-0"
          style={{
            background: 'rgb(var(--surface-2) / 0.74)',
            border: '1px solid rgb(var(--accent) / 0.34)',
            color: 'rgb(var(--accent))',
          }}
        >
          <Database className="w-4 h-4" strokeWidth={2.5} />
        </div>
        <span className="text-[14px] font-semibold tracking-tight truncate">dbview</span>
      </div>

      <button
        data-tour="command-palette-button"
        onClick={() => setCommandOpen(true)}
        className="hidden md:flex items-center gap-2.5 px-3 h-8 flex-1 max-w-[520px] rounded-md transition-colors hover:border-accent/40 group"
        style={{
          background: 'rgb(var(--surface-0) / 0.28)',
          border: '1px solid rgb(var(--border-subtle))',
          boxShadow: '0 1px 0 rgb(255 255 255 / 0.03) inset',
        }}
        aria-label="Open command palette"
        title="Open command palette"
      >
        <Command className="w-3.5 h-3.5 text-text-muted group-hover:text-accent transition-colors" />
        <span className="flex-1 text-left text-[12px] text-text-muted">Command palette</span>
      </button>

      <div className="flex items-center gap-2">
        <div className="hidden lg:flex metric-chip max-w-[280px]">
          <Activity className={isConnected ? 'w-3 h-3 text-success' : 'w-3 h-3 text-text-dim'} />
          <span className="truncate">
            {isConnected
              ? `${activeConnection.data!.dialect} / ${activeConnection.data!.name}`
              : 'no active connection'}
          </span>
        </div>
        <button
          onClick={toggleTheme}
          className="btn-icon relative overflow-hidden"
          aria-label={theme === 'dark' ? 'Switch to light theme' : 'Switch to dark theme'}
          title="Toggle theme"
        >
          <AnimatePresence initial={false} mode="wait">
            <motion.span
              key={theme}
              initial={{ opacity: 0, rotate: -45, scale: 0.8 }}
              animate={{ opacity: 1, rotate: 0, scale: 1 }}
              exit={{ opacity: 0, rotate: 45, scale: 0.8 }}
              transition={{ duration: 0.2, ease: [0.22, 1, 0.36, 1] }}
              className="inline-flex"
            >
              {theme === 'dark' ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
            </motion.span>
          </AnimatePresence>
        </button>
        <button
          onClick={() => setHistoryOpen(true)}
          className="btn-icon"
          aria-label="Query history"
          title="Query history"
        >
          <History className="w-4 h-4" />
        </button>
        <button
          onClick={() => setSettingsOpen(true)}
          className="btn-icon"
          aria-label="Settings"
          title="Settings"
        >
          <Settings className="w-4 h-4" />
        </button>
        <HelpMenu />
        <UserMenu />
      </div>
    </header>
  );
}
