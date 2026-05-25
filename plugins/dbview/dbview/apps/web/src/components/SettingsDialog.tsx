import { useState, useEffect } from 'react';
import * as Dialog from '@radix-ui/react-dialog';
import { AnimatePresence, motion } from 'framer-motion';
import { Eye, EyeOff, Globe, Key, Moon, Palette, Sparkles, Sun, X } from 'lucide-react';
import { toast } from 'sonner';
import { useAppStore } from '../store/app.js';
import { cn } from '../lib/cn.js';
import { AiProvidersSection } from './settings/AiProvidersSection.js';

const STORAGE_KEY = 'dbview_api_key';

export function SettingsDialog() {
  const open = useAppStore((s) => s.settingsOpen);
  const setOpen = useAppStore((s) => s.setSettingsOpen);
  const theme = useAppStore((s) => s.theme);
  const setTheme = useAppStore((s) => s.setTheme);
  const responseLocale = useAppStore((s) => s.responseLocale);
  const setResponseLocale = useAppStore((s) => s.setResponseLocale);
  const [apiKey, setApiKey] = useState('');
  const [reveal, setReveal] = useState(false);

  useEffect(() => {
    if (open) {
      setApiKey(localStorage.getItem(STORAGE_KEY) ?? '');
    }
  }, [open]);

  const save = () => {
    if (apiKey) localStorage.setItem(STORAGE_KEY, apiKey);
    else localStorage.removeItem(STORAGE_KEY);
    toast.success('Settings saved');
    setOpen(false);
  };

  return (
    // Non-modal Radix: in modal mode Radix locks body pointer-events. Combined
    // with AnimatePresence + forceMount, the lock can leak past close, freezing
    // the entire page. Backdrop close is wired manually below.
    <Dialog.Root open={open} onOpenChange={setOpen} modal={false}>
      <AnimatePresence>
        {open && (
          <Dialog.Portal forceMount>
            {/* Backdrop unmounts instantly on close so it never lingers as a
                fixed inset-0 click sink while the panel finishes its exit. */}
            <div
              onClick={() => setOpen(false)}
              className="fixed inset-0 z-40 bg-black/40 backdrop-blur-sm animate-fade-in"
              aria-hidden
            />
            <Dialog.Content className="fixed inset-0 z-50 grid place-items-center pointer-events-none focus:outline-none">
              <motion.div
                initial={{ opacity: 0, y: 8, scale: 0.985 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, y: 6, scale: 0.99 }}
                transition={{ duration: 0.22, ease: [0.22, 1, 0.36, 1] }}
                className="pointer-events-auto w-[560px] max-w-[92vw] rounded-lg border shadow-2xl overflow-hidden"
                style={{
                  background:
                    'linear-gradient(180deg, rgb(var(--surface-elevated)), rgb(var(--surface-1)))',
                  borderColor: 'rgb(var(--border-subtle))',
                }}
              >
                <div
                  className="flex items-center justify-between px-4 h-12 border-b"
                  style={{ borderColor: 'rgb(var(--border-subtle))' }}
                >
                  <Dialog.Title className="text-[14px] font-semibold">Settings</Dialog.Title>
                  <Dialog.Close className="btn-icon" aria-label="Close">
                    <X className="w-4 h-4" />
                  </Dialog.Close>
                </div>

                <div className="p-4 flex flex-col gap-5">
                  <Section icon={<Palette className="w-3.5 h-3.5" />} title="Appearance">
                    <div className="grid grid-cols-2 gap-2">
                      <ThemeButton
                        icon={<Moon className="w-4 h-4" />}
                        label="Dark"
                        active={theme === 'dark'}
                        onClick={() => setTheme('dark')}
                      />
                      <ThemeButton
                        icon={<Sun className="w-4 h-4" />}
                        label="Light"
                        active={theme === 'light'}
                        onClick={() => setTheme('light')}
                      />
                    </div>
                  </Section>

                  <Section
                    icon={<Globe className="w-3.5 h-3.5" />}
                    title={responseLocale === 'it' ? 'Lingua risposta' : 'Response language'}
                  >
                    <p className="text-[12px] text-text-muted">
                      {responseLocale === 'it'
                        ? "Lingua usata dall'assistente per riepiloghi e spiegazioni. La query generata resta sempre nel linguaggio del database (SQL/Cypher/Qdrant)."
                        : 'Language the assistant uses for summaries and explanations. The generated query is always in the database language (SQL/Cypher/Qdrant).'}
                    </p>
                    <div className="grid grid-cols-2 gap-2">
                      <LocaleButton
                        flag="🇬🇧"
                        label="English"
                        active={responseLocale === 'en'}
                        onClick={() => setResponseLocale('en')}
                      />
                      <LocaleButton
                        flag="🇮🇹"
                        label="Italiano"
                        active={responseLocale === 'it'}
                        onClick={() => setResponseLocale('it')}
                      />
                    </div>
                  </Section>

                  <Section icon={<Sparkles className="w-3.5 h-3.5" />} title="AI Providers">
                    <p className="text-[12px] text-text-muted">
                      Save your OpenAI and Anthropic API keys to use them for NL2SQL. Keys are
                      encrypted at rest with the server&apos;s{' '}
                      <code className="font-mono">DBVIEW_SECRET</code> and stay per-user. The
                      environment variables <code className="font-mono">OPENAI_API_KEY</code> /{' '}
                      <code className="font-mono">ANTHROPIC_API_KEY</code> still act as fallback.
                    </p>
                    <AiProvidersSection />
                  </Section>

                  <Section icon={<Key className="w-3.5 h-3.5" />} title="dbview API Key">
                    <p className="text-[12px] text-text-muted">
                      Sent as <code className="font-mono text-text">X-API-Key</code> header.
                      Required when
                      <code className="font-mono text-text"> DBVIEW_API_KEY</code> is configured
                      server-side.
                    </p>
                    <div className="relative">
                      <input
                        type={reveal ? 'text' : 'password'}
                        className="input pr-10 font-mono"
                        placeholder="paste API key…"
                        value={apiKey}
                        onChange={(e) => setApiKey(e.target.value)}
                        autoComplete="off"
                      />
                      <button
                        type="button"
                        className="absolute right-2 top-1/2 -translate-y-1/2 btn-icon w-7 h-7"
                        onClick={() => setReveal(!reveal)}
                        aria-label={reveal ? 'Hide' : 'Reveal'}
                      >
                        {reveal ? (
                          <EyeOff className="w-3.5 h-3.5" />
                        ) : (
                          <Eye className="w-3.5 h-3.5" />
                        )}
                      </button>
                    </div>
                  </Section>
                </div>

                <div
                  className="flex items-center justify-end gap-2 px-4 h-12 border-t"
                  style={{ borderColor: 'rgb(var(--border-subtle))' }}
                >
                  <Dialog.Close className="btn">Cancel</Dialog.Close>
                  <button onClick={save} className="btn-primary">
                    Save
                  </button>
                </div>
              </motion.div>
            </Dialog.Content>
          </Dialog.Portal>
        )}
      </AnimatePresence>
    </Dialog.Root>
  );
}

function Section({
  icon,
  title,
  children,
}: {
  icon: React.ReactNode;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div
      className="flex flex-col gap-2 rounded-lg border p-3"
      style={{
        background: 'rgb(var(--surface-2) / 0.34)',
        borderColor: 'rgb(var(--border-subtle))',
      }}
    >
      <div className="flex items-center gap-1.5 text-[11px] uppercase tracking-wider text-text-dim">
        {icon}
        <span>{title}</span>
      </div>
      {children}
    </div>
  );
}

function LocaleButton({
  flag,
  label,
  active,
  onClick,
}: {
  flag: string;
  label: string;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={cn(
        'flex items-center gap-2 px-3 h-10 rounded-md transition-colors border',
        active ? 'ring-1 ring-accent/50' : 'hover:bg-surface-2'
      )}
      style={{
        background: active
          ? 'linear-gradient(135deg, rgb(var(--accent) / 0.14), rgb(var(--brand) / 0.08))'
          : 'rgb(var(--surface-2) / 0.84)',
        color: active ? 'rgb(var(--accent))' : 'rgb(var(--text-muted))',
        borderColor: active ? 'rgb(var(--accent) / 0.5)' : 'rgb(var(--border-subtle))',
      }}
    >
      <span className="text-[16px] leading-none">{flag}</span>
      <span className="text-[13px] font-medium">{label}</span>
    </button>
  );
}

function ThemeButton({
  icon,
  label,
  active,
  onClick,
}: {
  icon: React.ReactNode;
  label: string;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={cn(
        'flex items-center gap-2 px-3 h-10 rounded-md transition-colors border',
        active ? 'ring-1 ring-accent/50' : 'hover:bg-surface-2'
      )}
      style={{
        background: active
          ? 'linear-gradient(135deg, rgb(var(--accent) / 0.14), rgb(var(--brand) / 0.08))'
          : 'rgb(var(--surface-2) / 0.84)',
        color: active ? 'rgb(var(--accent))' : 'rgb(var(--text-muted))',
        borderColor: active ? 'rgb(var(--accent) / 0.5)' : 'rgb(var(--border-subtle))',
      }}
    >
      {icon}
      <span className="text-[13px] font-medium">{label}</span>
    </button>
  );
}
