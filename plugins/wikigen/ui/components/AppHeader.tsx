import {
  Command,
  FileText,
  HelpCircle,
  Network,
  PanelTop,
  ShieldCheck,
  Sliders,
  Sparkles,
  Upload,
} from 'lucide-react';
import { Can } from './Can';
import { EditionSelector, type EditionOption } from './EditionSelector';
import { StatusPill } from './StatusPill';
import { ThemeToggle } from './ThemeToggle';
import { UserMenu } from './UserMenu';
import { navigate } from '../hooks/useLocation';
import type { Conversation } from '../lib/types';

export function AppHeader({
  active,
  messageUserCount,
  onOpenPalette,
  onOpenUpload,
  onOpenWizard,
  onOpenSettings,
  onOpenHelp,
  onOpenMemories,
  editions,
  editionId,
  setEditionId,
  allSourcesCount,
  sourcesOpen,
  onOpenSources,
}: {
  active: Conversation | null | undefined;
  messageUserCount: number;
  onOpenPalette: () => void;
  onOpenUpload: () => void;
  onOpenWizard: () => void;
  onOpenSettings: () => void;
  onOpenHelp: () => void;
  onOpenMemories: () => void;
  editions: EditionOption[];
  editionId: string;
  setEditionId: (id: string) => void;
  allSourcesCount: number;
  sourcesOpen: boolean;
  onOpenSources: () => void;
}) {
  return (
    <header
      className="sticky top-0 z-30 border-b border-[var(--color-border)]
                 bg-[var(--color-canvas)]/82 backdrop-blur-xl shadow-[0_1px_0_rgba(255,255,255,0.5)]"
    >
      <div className="flex min-h-[4.25rem] flex-wrap items-center justify-between gap-3 px-4 py-2.5 sm:px-6">
        <div className="flex min-w-0 items-center gap-3">
          <div className="hidden size-9 shrink-0 place-items-center rounded-lg border border-[var(--color-border)] bg-[var(--color-canvas-raised)] text-[var(--color-brand)] shadow-[var(--shadow-xs)] sm:grid">
            <PanelTop size={16} aria-hidden />
          </div>
          <div className="flex min-w-0 flex-col leading-tight">
            <span className="text-[10px] font-semibold uppercase tracking-[0.14em] text-ink-subtle">
              Conversazione
            </span>
            <span className="font-display max-w-[38vw] truncate text-[16px] font-bold tracking-[-0.01em] text-ink sm:max-w-[24rem]">
              {active?.title ?? 'Nuova conversazione'}
            </span>
          </div>
          {messageUserCount > 0 && (
            <span className="chip hidden tabular-nums lg:inline-flex">
              {messageUserCount} {messageUserCount === 1 ? 'domanda' : 'domande'}
            </span>
          )}
        </div>

        <div className="flex min-w-0 items-center gap-2">
          <Can perm="view.command_palette">
            <button
              onClick={onOpenPalette}
              className="btn-secondary hidden sm:inline-flex"
              title="apri tavolozza comandi ⌘/"
              aria-label="apri tavolozza comandi"
            >
              <Command size={13} />
              Comandi
            </button>
          </Can>
          <div className="flex items-center gap-1 rounded-lg border border-[var(--color-border)] bg-[var(--color-canvas-raised)] p-1 shadow-[var(--shadow-xs)]">
            <Can perm="ingest.run">
              <button
                onClick={onOpenUpload}
                className="btn-icon !size-8 !rounded-md"
                title="carica documento ⌘U"
                aria-label="carica documento"
              >
                <Upload size={14} />
              </button>
            </Can>
            <Can perm="graph.read">
              <button
                onClick={() => navigate('/graph')}
                className="btn-icon !size-8 !rounded-md"
                title="knowledge graph"
                aria-label="knowledge graph"
              >
                <Network size={14} />
              </button>
            </Can>
            <Can perm="view.sources">
              {allSourcesCount > 0 && (
                <button
                  onClick={onOpenSources}
                  className="btn-icon !size-8 !rounded-md"
                  title={`fonti citate: ${allSourcesCount}`}
                  aria-label="apri pannello fonti"
                  aria-expanded={sourcesOpen}
                >
                  <span className="relative inline-flex">
                    <FileText size={14} />
                    <span className="absolute -right-2 -top-2 min-w-3 rounded-full bg-[var(--color-brand)] px-0.5 text-center text-[8px] font-bold leading-3 text-white">
                      {allSourcesCount > 9 ? '9+' : allSourcesCount}
                    </span>
                  </span>
                </button>
              )}
            </Can>
            <Can perm="admin.scaffold">
              <span aria-hidden className="mx-0.5 h-5 w-px bg-[var(--color-border)]" />
              <button
                onClick={onOpenWizard}
                className="btn-icon !size-8 !rounded-md"
                title="crea nuova wiki ⌘⇧N"
                aria-label="crea nuova wiki"
              >
                <Sparkles size={14} />
              </button>
            </Can>
            <Can perm="admin.user.manage">
              <button
                onClick={() => navigate('/admin/users')}
                className="btn-icon !size-8 !rounded-md"
                title="gestione utenti e ruoli"
                aria-label="gestione utenti e ruoli"
              >
                <ShieldCheck size={14} />
              </button>
            </Can>
            <span aria-hidden className="mx-0.5 h-5 w-px bg-[var(--color-border)]" />
            <Can perm="view.settings">
              <button
                onClick={onOpenSettings}
                className="btn-icon !size-8 !rounded-md"
                title="impostazioni ⌘,"
                aria-label="impostazioni"
              >
                <Sliders size={14} />
              </button>
            </Can>
            <Can perm="view.help">
              <button
                onClick={onOpenHelp}
                className="btn-icon !size-8 !rounded-md"
                title="scorciatoie tastiera (?)"
                aria-label="scorciatoie tastiera"
              >
                <HelpCircle size={14} />
              </button>
            </Can>
          </div>
          {editions.length > 0 && (
            <Can perm="view.editions">
              <EditionSelector editions={editions} value={editionId} onChange={setEditionId} />
            </Can>
          )}
          <ThemeToggle />
          <Can perm="view.status">
            <StatusPill compact />
          </Can>
          <UserMenu onOpenMemories={onOpenMemories} />
        </div>
      </div>
    </header>
  );
}
