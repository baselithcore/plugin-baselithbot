/**
 * One-shot helper: migra cronologia localStorage pre-Fase 6 → backend
 * Postgres al primo login.
 *
 * Trigger: chiamato dal bootstrap di `useConversations` quando rileva
 * `user` appena loggato e localStorage contiene il payload legacy
 * (chiave `llm-wiki:conversations` SENZA suffisso `:user:<id>`).
 *
 * Strategia
 * =========
 * 1. Legge il payload legacy (anonimo, pre-Fase 6).
 * 2. Per ogni conversation locale: crea su backend con stesso titolo +
 *    pinned/title_locked, poi POSTa in ordine cronologico ogni message.
 * 3. Marca migration done con flag dedicato in localStorage:
 *    `llm-wiki:legacy-migrated:user:<id>` — evita re-run anche se
 *    qualcuno reinserisce dati nella vecchia chiave.
 * 4. NON cancella la chiave legacy: l'utente può sempre tornare alla
 *    versione precedente del frontend e riavere la cronologia. Comunque
 *    il flag impedisce import duplicato.
 *
 * Errori non bloccano l'app: vengono solo loggati. La cronologia
 * legacy resta nel browser; l'utente vede UI vuota e può continuare.
 */

import {
  type ApiConversation,
  createConversation,
  updateConversation,
} from './api/conversations';
import { authFetch } from './api/client';

const LEGACY_KEY = 'llm-wiki:conversations';
const FLAG_KEY = (userId: string) => `llm-wiki:legacy-migrated:user:${userId}`;

interface LegacyMessage {
  id?: string;
  role: 'user' | 'assistant';
  content: string;
  createdAt?: number;
  sources?: unknown[];
}

interface LegacyConversation {
  id: string;
  title: string;
  messages: LegacyMessage[];
  createdAt?: number;
  updatedAt?: number;
  titleLocked?: boolean;
  pinned?: boolean;
}

export interface MigrationResult {
  conversations_imported: number;
  messages_imported: number;
  errors: string[];
  skipped: boolean;
}

export async function migrateLegacyConversations(
  userId: string
): Promise<MigrationResult> {
  const result: MigrationResult = {
    conversations_imported: 0,
    messages_imported: 0,
    errors: [],
    skipped: false,
  };

  try {
    if (localStorage.getItem(FLAG_KEY(userId))) {
      result.skipped = true;
      return result;
    }
  } catch {
    // localStorage indisponibile (modalità privata estrema) — skip.
    result.skipped = true;
    return result;
  }

  let legacy: LegacyConversation[] = [];
  try {
    const raw = localStorage.getItem(LEGACY_KEY);
    if (!raw) {
      // Nulla da migrare. Marca comunque per non ri-tentare ad ogni boot.
      localStorage.setItem(FLAG_KEY(userId), '1');
      result.skipped = true;
      return result;
    }
    legacy = JSON.parse(raw) as LegacyConversation[];
    if (!Array.isArray(legacy) || legacy.length === 0) {
      localStorage.setItem(FLAG_KEY(userId), '1');
      result.skipped = true;
      return result;
    }
  } catch (err) {
    result.errors.push(`parse legacy storage: ${(err as Error).message}`);
    localStorage.setItem(FLAG_KEY(userId), '1'); // non ritentare su payload corrotto
    return result;
  }

  // Importa in ordine cronologico (createdAt asc) così la sidebar
  // mostra le più vecchie in fondo come ci si aspetta.
  legacy.sort((a, b) => (a.createdAt ?? 0) - (b.createdAt ?? 0));

  for (const conv of legacy) {
    try {
      const created: ApiConversation = await createConversation(
        conv.title || 'Conversazione importata'
      );
      result.conversations_imported += 1;

      if (conv.titleLocked || conv.pinned) {
        try {
          await updateConversation(created.id, {
            title_locked: conv.titleLocked,
            pinned: conv.pinned,
          });
        } catch {
          /* non-bloccante */
        }
      }

      // Append messages in ordine cronologico.
      const msgs = (conv.messages ?? []).slice().sort(
        (a, b) => (a.createdAt ?? 0) - (b.createdAt ?? 0)
      );
      for (const m of msgs) {
        if (!m.content?.trim()) continue;
        try {
          await postMessage(created.id, {
            role: m.role,
            content: m.content,
            sources: m.sources ?? null,
          });
          result.messages_imported += 1;
        } catch (err) {
          result.errors.push(
            `messaggio in conv "${conv.title}": ${(err as Error).message}`
          );
        }
      }
    } catch (err) {
      result.errors.push(
        `conversation "${conv.title}": ${(err as Error).message}`
      );
    }
  }

  // Marca done anche con errori parziali — evita loop infinito.
  // L'utente vede risultato (toast) e può ripetere manualmente se serve.
  try {
    localStorage.setItem(FLAG_KEY(userId), '1');
  } catch {
    /* ignore */
  }

  return result;
}

async function postMessage(
  conversationId: string,
  body: { role: string; content: string; sources?: unknown[] | null }
): Promise<void> {
  const r = await authFetch(
    `/conversations/${encodeURIComponent(conversationId)}/messages`,
    {
      method: 'POST',
      body: JSON.stringify(body),
    }
  );
  if (!r.ok) {
    throw new Error(`HTTP ${r.status}`);
  }
}
