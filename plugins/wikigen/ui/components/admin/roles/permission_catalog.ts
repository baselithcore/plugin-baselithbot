import {
  BookOpenText,
  ClipboardList,
  Eye,
  FileLock2,
  FilePlus2,
  KeyRound,
  MessageSquare,
  type LucideIcon,
  Network,
  ShieldCheck,
  Sparkles,
  UserCog,
} from 'lucide-react';

export interface GroupMeta {
  id: string;
  label: string;
  icon: LucideIcon;
  description: string;
  /**
   * UI surface (tab / page / drawer) toggled by this permission family.
   * Lets the role editor surface "this controls which tabs the role
   * sees" in line with modern RBAC UIs (Notion, Linear, GitHub) where
   * each permission is annotated with the affected surface.
   */
  tabs?: string[];
}

export const GROUP_META: Record<string, GroupMeta> = {
  wiki: {
    id: 'wiki',
    label: 'Wiki',
    icon: BookOpenText,
    description: 'Lettura, scrittura ed eliminazione di pagine del vault.',
    tabs: ['Sidebar pagine', 'Citazioni / Fonti'],
  },
  chat: {
    id: 'chat',
    label: 'Chat / RAG',
    icon: MessageSquare,
    description: 'Uso dell’assistente conversazionale.',
    tabs: ['Tab Chat', 'Composer'],
  },
  ingest: {
    id: 'ingest',
    label: 'Ingest',
    icon: FilePlus2,
    description: 'Caricamento ed eliminazione di documenti grezzi.',
    tabs: ['Pulsante carica documento', 'Modale upload'],
  },
  conversation: {
    id: 'conversation',
    label: 'Conversazioni',
    icon: ClipboardList,
    description: 'Cronologia delle conversazioni utente.',
    tabs: ['Sidebar conversazioni'],
  },
  feedback: {
    id: 'feedback',
    label: 'Feedback',
    icon: Sparkles,
    description: 'Raccolta e gestione del feedback sugli output del modello.',
    tabs: ['Bottoni 👍/👎 sui messaggi', 'Moderazione feedback'],
  },
  memory: {
    id: 'memory',
    label: 'Memorie',
    icon: KeyRound,
    description: 'Memorie personalizzate disponibili al RAG.',
    tabs: ['Drawer Memorie'],
  },
  graph: {
    id: 'graph',
    label: 'Knowledge Graph',
    icon: Network,
    description: 'Visualizzazione e navigazione del grafo entità/relazioni.',
    tabs: ['Tab Grafo', 'Pagina /graph'],
  },
  admin: {
    id: 'admin',
    label: 'Amministrazione',
    icon: UserCog,
    description: 'Operazioni di gestione del tenant e degli utenti.',
    tabs: [
      'Wizard nuova wiki',
      'Gestione utenti',
      'Settings → sezione tenant',
      'Restart runtime',
    ],
  },
  rbac: {
    id: 'rbac',
    label: 'RBAC',
    icon: ShieldCheck,
    description: 'Assegnazione di ruoli system gerarchici.',
    tabs: ['Pagina /admin/roles', 'Assegnazione ruoli'],
  },
  obsidian: {
    id: 'obsidian',
    label: 'Obsidian',
    icon: FileLock2,
    description: 'Apertura del vault nel client desktop Obsidian.',
    tabs: ['Pulsante "Apri in Obsidian" su ogni pagina'],
  },
  view: {
    id: 'view',
    label: 'Visibilità UI',
    icon: Eye,
    description:
      'Mostra / nasconde pulsanti e pannelli della home (header, modali). Pattern Notion/Linear: composizione di profili stretti.',
    tabs: [
      'Pulsante Impostazioni',
      'Pulsante Help / shortcuts',
      'Tavolozza comandi (⌘/)',
      'Pannello Fonti',
      'Indicatore di stato',
      'Selettore edizione',
    ],
  },
};

export const FALLBACK_GROUP: GroupMeta = {
  id: 'altro',
  label: 'Altro',
  icon: Network,
  description: 'Permessi non categorizzati.',
};

/** Slug-level Italian descriptions. Fallback to client-side derivation if missing. */
export const PERMISSION_DESCRIPTIONS: Record<string, string> = {
  'wiki.read': 'Leggi pagine wiki del dominio',
  'wiki.write': 'Crea e modifica pagine wiki',
  'wiki.delete': 'Elimina pagine wiki',
  'chat.use': 'Avvia conversazioni con l’assistente',
  'ingest.run': 'Avvia pipeline di ingest su nuovi documenti',
  'ingest.delete': 'Elimina documenti grezzi dal vault',
  'conversation.read': 'Leggi cronologia delle conversazioni',
  'conversation.delete': 'Elimina conversazioni',
  'feedback.write': 'Invia feedback su risposte e citazioni',
  'feedback.read': 'Leggi feedback aggregato',
  'feedback.delete': 'Modera ed elimina feedback',
  'memory.read': 'Leggi memorie personalizzate',
  'memory.write': 'Crea e modifica memorie',
  'memory.delete': 'Elimina memorie',
  'admin.scaffold': 'Crea nuovi domini (scaffold pack)',
  'admin.tenant.manage': 'Gestisci configurazione tenant',
  'admin.user.manage': 'Gestisci utenti e inviti',
  'admin.runtime': 'Controlla runtime: restart worker, autostart',
  'admin.audit.read': 'Consulta log di audit',
  'obsidian.open': 'Apri pagine nel client desktop Obsidian',
  'graph.read': 'Visualizza il grafo conoscenze (entità, relazioni, comunità)',
  'view.settings': 'Mostra il pulsante Impostazioni nell\'header',
  'view.help': 'Mostra il pulsante Help / scorciatoie',
  'view.command_palette': 'Mostra la tavolozza comandi (⌘/)',
  'view.sources': 'Mostra il pannello Fonti / citazioni',
  'view.status': 'Mostra l\'indicatore di stato del deploy',
  'view.editions': 'Mostra il selettore di edizione / dominio',
  'rbac.assign.superuser': 'Assegna il ruolo superuser',
  'rbac.assign.admin': 'Assegna il ruolo admin',
  'rbac.assign.moderator': 'Assegna il ruolo moderator',
  'rbac.assign.user': 'Assegna il ruolo user',
};

export function describePermission(slug: string, fallback?: string): string {
  return PERMISSION_DESCRIPTIONS[slug] || fallback || slug;
}

export function groupForSlug(slug: string): GroupMeta {
  const prefix = slug.split('.')[0];
  return GROUP_META[prefix] ?? FALLBACK_GROUP;
}

const GROUP_ORDER = [
  'view',
  'wiki',
  'chat',
  'ingest',
  'conversation',
  'feedback',
  'memory',
  'graph',
  'admin',
  'rbac',
  'obsidian',
];

export function groupSortKey(groupId: string): number {
  const i = GROUP_ORDER.indexOf(groupId);
  return i === -1 ? 999 : i;
}
