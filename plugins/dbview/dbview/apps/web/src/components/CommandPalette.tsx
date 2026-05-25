import { Command } from 'cmdk';
import { useQuery } from '@tanstack/react-query';
import * as Dialog from '@radix-ui/react-dialog';
import { AnimatePresence, motion } from 'framer-motion';
import { Database, Moon, Settings, Sparkles, Sun } from 'lucide-react';
import { api } from '../lib/api.js';
import { useAppStore } from '../store/app.js';

export function CommandPalette() {
  // ⌘K toggling happens in App.tsx so the palette can stay a lazy chunk.
  const open = useAppStore((s) => s.commandOpen);
  const setOpen = useAppStore((s) => s.setCommandOpen);
  const setActive = useAppStore((s) => s.setActiveConnection);
  const toggleTheme = useAppStore((s) => s.toggleTheme);
  const setSettingsOpen = useAppStore((s) => s.setSettingsOpen);
  const theme = useAppStore((s) => s.theme);

  const conns = useQuery({ queryKey: ['connections'], queryFn: api.listConnections });

  return (
    // modal={false} so Radix never locks body pointer-events. Backdrop close
    // is wired manually below.
    <Dialog.Root open={open} onOpenChange={setOpen} modal={false}>
      <AnimatePresence>
        {open && (
          <Dialog.Portal forceMount>
            <div
              onClick={() => setOpen(false)}
              className="fixed inset-0 z-40 bg-black/40 backdrop-blur-sm animate-fade-in"
              aria-hidden
            />
            <Dialog.Content className="fixed inset-0 z-50 flex items-start justify-center pt-[18vh] pointer-events-none focus:outline-none">
              <motion.div
                initial={{ opacity: 0, y: 12, scale: 0.985 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, y: 8, scale: 0.99 }}
                transition={{ duration: 0.22, ease: [0.22, 1, 0.36, 1] }}
                className="pointer-events-auto w-[680px] max-w-[92vw] rounded-lg border shadow-2xl overflow-hidden"
                style={{
                  background:
                    'linear-gradient(180deg, rgb(var(--surface-elevated)), rgb(var(--surface-1)))',
                  borderColor: 'rgb(var(--border-subtle))',
                }}
              >
                <Dialog.Title className="sr-only">Command palette</Dialog.Title>
                <Command className="flex flex-col" loop>
                  <div
                    className="flex items-center gap-2 px-3 h-12 border-b"
                    style={{ borderColor: 'rgb(var(--border-subtle))' }}
                  >
                    <Sparkles className="w-4 h-4 text-text-muted" />
                    <Command.Input
                      placeholder="Search connections, actions…"
                      className="flex-1 bg-transparent outline-none text-[14px] placeholder:text-text-dim"
                    />
                    <span className="kbd">esc</span>
                  </div>
                  <Command.List className="max-h-[380px] overflow-auto p-2">
                    <Command.Empty className="px-3 py-6 text-center text-[12px] text-text-dim">
                      No results.
                    </Command.Empty>

                    {conns.data && conns.data.length > 0 && (
                      <Command.Group
                        heading="Connections"
                        className="text-[10px] uppercase tracking-wider text-text-dim px-2 py-1.5"
                      >
                        {conns.data.map((c) => (
                          <Command.Item
                            key={c.id}
                            value={`${c.name} ${c.dialect} ${c.displayDatabase ?? ''}`}
                            onSelect={() => {
                              setActive(c.id);
                              setOpen(false);
                            }}
                            className="flex items-center gap-3 px-2.5 py-2.5 rounded-md cursor-pointer data-[selected=true]:bg-surface-2"
                          >
                            <Database className="w-3.5 h-3.5 text-text-muted" />
                            <div className="flex-1">
                              <div className="text-[13px]">{c.name}</div>
                              <div className="text-[10px] font-mono text-text-dim">
                                {c.dialect} · {c.displayDatabase ?? '—'}
                              </div>
                            </div>
                          </Command.Item>
                        ))}
                      </Command.Group>
                    )}

                    <Command.Group
                      heading="Actions"
                      className="text-[10px] uppercase tracking-wider text-text-dim px-2 py-1.5"
                    >
                      <Command.Item
                        value="toggle theme"
                        onSelect={() => {
                          toggleTheme();
                          setOpen(false);
                        }}
                        className="flex items-center gap-3 px-2.5 py-2.5 rounded-md cursor-pointer data-[selected=true]:bg-surface-2"
                      >
                        {theme === 'dark' ? (
                          <Sun className="w-3.5 h-3.5 text-text-muted" />
                        ) : (
                          <Moon className="w-3.5 h-3.5 text-text-muted" />
                        )}
                        <span className="text-[13px]">
                          Switch to {theme === 'dark' ? 'light' : 'dark'} theme
                        </span>
                      </Command.Item>
                      <Command.Item
                        value="settings"
                        onSelect={() => {
                          setSettingsOpen(true);
                          setOpen(false);
                        }}
                        className="flex items-center gap-3 px-2.5 py-2.5 rounded-md cursor-pointer data-[selected=true]:bg-surface-2"
                      >
                        <Settings className="w-3.5 h-3.5 text-text-muted" />
                        <span className="text-[13px]">Open settings</span>
                      </Command.Item>
                    </Command.Group>
                  </Command.List>
                </Command>
              </motion.div>
            </Dialog.Content>
          </Dialog.Portal>
        )}
      </AnimatePresence>
    </Dialog.Root>
  );
}
