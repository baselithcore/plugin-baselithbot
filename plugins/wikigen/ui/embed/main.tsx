/**
 * Embed bootstrap: legge ``?token=...`` da URL, monta ``<EmbedChat />``.
 *
 * Pattern: questo file è un Vite entry separato dall'SPA principale. Il
 * bundle prodotto NON include sidebar/admin/wizard — solo chat UI.
 */

import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';

import { EmbedChat } from './EmbedChat';

function readToken(): string | null {
  const params = new URLSearchParams(window.location.search);
  const t = params.get('token');
  if (t && t.startsWith('emb_') && t.length >= 16) {
    return t;
  }
  return null;
}

function renderError(container: HTMLElement, msg: string): void {
  // Costruisce DOM con createElement — niente innerHTML su input
  // user-controlled (msg arriva da messaggi locali in italiano, ma
  // safety-by-default).
  container.textContent = '';
  const box = document.createElement('div');
  box.style.padding = '24px';
  box.style.fontFamily = 'sans-serif';
  box.style.color = '#b91c1c';
  const title = document.createElement('h3');
  title.style.margin = '0 0 8px 0';
  title.textContent = 'Configurazione non valida';
  const body = document.createElement('p');
  body.style.margin = '0';
  body.style.fontSize = '14px';
  body.textContent = msg;
  box.appendChild(title);
  box.appendChild(body);
  container.appendChild(box);
}

const token = readToken();
const container = document.getElementById('embed-root');

if (container && !token) {
  renderError(container, "Token mancante o malformato. L'embed richiede ?token=emb_… nella URL.");
} else if (container && token) {
  createRoot(container).render(
    <StrictMode>
      <EmbedChat token={token} />
    </StrictMode>
  );
}
