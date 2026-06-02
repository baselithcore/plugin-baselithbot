import type { Conversation, Message } from './types';

/**
 * Serializza una conversazione in Markdown formale. Formato pensato per:
 * - archiviazione della consulenza (audit trail)
 * - condivisione con ufficio sinistri/legale
 *
 * Le citazioni inline `[[x]]` sono preservate così da restare navigabili
 * una volta riaperte in Obsidian. In fondo, sezione "Fonti" elencata.
 */
export function conversationToMarkdown(conv: Conversation): string {
  const out: string[] = [];
  const created = new Date(conv.createdAt).toLocaleString('it-IT');
  const updated = new Date(conv.updatedAt).toLocaleString('it-IT');

  out.push(`# ${conv.title}`);
  out.push('');
  out.push(`> Conversazione LLM Wiki · creata ${created} · aggiornata ${updated}`);
  out.push('');

  conv.messages.forEach((m, i) => {
    const label = m.role === 'user' ? 'Domanda' : 'Risposta';
    const ts = new Date(m.createdAt).toLocaleTimeString('it-IT');
    out.push(`## ${label} ${messageNumber(conv.messages, i)} — ${ts}`);
    out.push('');
    out.push(m.content.trim() || '_(vuoto)_');
    out.push('');
    if (m.error) out.push(`> [!warning] Errore durante la generazione: ${m.error}`);
    if (m.role === 'assistant' && m.sources && m.sources.length > 0) {
      out.push('**Fonti recuperate:**');
      out.push('');
      m.sources.forEach((s, j) => {
        const bits = [
          s.edizione ? `Ed. ${s.edizione}` : null,
          s.rango ? `rango: ${s.rango}` : null,
          s.score != null ? `score: ${s.score.toFixed(2)}` : null,
          s.via_rinvio ? 'via rinvio' : null,
        ].filter(Boolean);
        out.push(
          `${j + 1}. [[${s.document_id}|${s.title}]]${bits.length ? ' — ' + bits.join(' · ') : ''}`
        );
      });
      out.push('');
    }
  });

  out.push('---');
  out.push('');
  out.push(
    '_Export generato da LLM Wiki. Le risposte non sostituiscono il parere di un agente o legale._'
  );
  return out.join('\n');
}

function messageNumber(all: Message[], idx: number): number {
  const role = all[idx].role;
  let n = 0;
  for (let i = 0; i <= idx; i++) if (all[i].role === role) n++;
  return n;
}

export function downloadMarkdown(conv: Conversation) {
  const md = conversationToMarkdown(conv);
  const safeTitle = conv.title
    .replace(/[^a-zA-Z0-9\-_ ]/g, '')
    .trim()
    .replace(/\s+/g, '-')
    .toLowerCase();
  const name = `conversazione-${safeTitle || conv.id.slice(0, 8)}.md`;
  const blob = new Blob([md], { type: 'text/markdown;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = name;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 0);
}
