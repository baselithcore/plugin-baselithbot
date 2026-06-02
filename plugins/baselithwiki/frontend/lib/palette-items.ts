import {
  FileText,
  HelpCircle,
  MessagesSquare,
  PanelLeft,
  Plus,
  Settings as SettingsIcon,
  Sliders,
  Sparkles,
  Upload,
} from 'lucide-react';
import type { CommandItem } from '../components/CommandPalette';
import { DEFAULT_SETTINGS, type Settings } from '../components/SettingsModal';
import type { Conversation } from './types';

interface PaletteFactoryArgs {
  conversations: Conversation[];
  setSettings: (s: Settings) => void;
  setActiveId: (id: string) => void;
  setSidebarOpen: (fn: (v: boolean) => boolean) => void;
  setSourcesOpen: (fn: (v: boolean) => boolean) => void;
  openUpload: () => void;
  openWizard: () => void;
  openSettings: () => void;
  openHelp: () => void;
  newChat: () => void;
}

/**
 * Builds the command palette items list. Pure factory: no side-effects, just
 * a list of action handlers wired to the parent component callbacks.
 */
export function buildPaletteItems({
  conversations,
  setSettings,
  setActiveId,
  setSidebarOpen,
  setSourcesOpen,
  openUpload,
  openWizard,
  openSettings,
  openHelp,
  newChat,
}: PaletteFactoryArgs): CommandItem[] {
  const cmds: CommandItem[] = [
    {
      id: 'new-chat',
      label: 'Nuova conversazione',
      hint: '⌘K',
      icon: Plus,
      group: 'Azioni',
      keywords: 'nuova chat',
      onRun: newChat,
    },
    {
      id: 'toggle-sidebar',
      label: 'Mostra/nascondi sidebar',
      hint: '⌘B',
      icon: PanelLeft,
      group: 'Azioni',
      onRun: () => setSidebarOpen((v) => !v),
    },
    {
      id: 'toggle-sources',
      label: 'Apri/chiudi pannello fonti',
      icon: FileText,
      group: 'Azioni',
      onRun: () => setSourcesOpen((v) => !v),
    },
    {
      id: 'upload-raw',
      label: 'Carica documento nel vault',
      hint: '⌘U',
      icon: Upload,
      group: 'Azioni',
      keywords: 'upload ingest pdf raw documento fonte',
      onRun: openUpload,
    },
    {
      id: 'new-wiki',
      label: 'Crea nuova wiki…',
      hint: '⌘⇧N',
      icon: Sparkles,
      group: 'Azioni',
      keywords: 'wizard scaffold nuovo dominio domain pack tenant white-label',
      onRun: openWizard,
    },
    {
      id: 'settings',
      label: 'Impostazioni',
      hint: '⌘,',
      icon: Sliders,
      group: 'Azioni',
      keywords: 'settings top-k retrieval graph',
      onRun: openSettings,
    },
    {
      id: 'help',
      label: 'Scorciatoie da tastiera',
      hint: '?',
      icon: HelpCircle,
      group: 'Aiuto',
      onRun: openHelp,
    },
    {
      id: 'reset-settings',
      label: 'Ripristina impostazioni predefinite',
      icon: SettingsIcon,
      group: 'Aiuto',
      keywords: 'reset default',
      onRun: () => setSettings(DEFAULT_SETTINGS),
    },
  ];
  const convs: CommandItem[] = conversations.slice(0, 30).map((c) => ({
    id: `conv-${c.id}`,
    label: c.title || 'Senza titolo',
    icon: MessagesSquare,
    group: 'Conversazioni',
    keywords: c.messages.map((m) => m.content.slice(0, 100)).join(' '),
    onRun: () => setActiveId(c.id),
  }));
  return [...cmds, ...convs];
}
