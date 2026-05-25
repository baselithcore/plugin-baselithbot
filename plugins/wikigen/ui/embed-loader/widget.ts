/**
 * Wiki Chat embed widget loader.
 *
 * Uso:
 *
 *   <script src="https://wiki.example.com/embed.js"
 *           data-token="emb_xxx"
 *           data-position="bottom-right"
 *           data-color="#0ea5e9"
 *           data-label="Chat con noi"></script>
 *
 * Behavior:
 *
 * 1. Cerca il proprio <script> via ``document.currentScript`` e legge i
 *    ``data-*`` attribute.
 * 2. Inietta un bottone fluttuante + un iframe nascosto (display:none)
 *    nella corner configurata.
 * 3. Click sul bottone → mostra l'iframe.
 * 4. postMessage ``embed:close`` dall'iframe → nasconde iframe.
 *
 * NB: lo script gira nel contesto del sito ospitante. Nessuna dipendenza
 * (React/etc) — bundle ~2-3 KB gzipped target.
 */

interface WidgetConfig {
  token: string;
  origin: string; // base URL del wiki (es. https://wiki.example.com)
  position: 'bottom-right' | 'bottom-left';
  color: string;
  label: string;
  width: number;
  height: number;
}

const POSITION_VALUES = ['bottom-right', 'bottom-left'] as const;

function readConfig(): WidgetConfig | null {
  const script = (document.currentScript as HTMLScriptElement | null) ?? findScriptFallback();
  if (!script) return null;

  const token = (script.dataset.token ?? '').trim();
  if (!token || !token.startsWith('emb_')) {
    console.warn('[wiki-embed] data-token mancante o malformato; widget non caricato.');
    return null;
  }

  // Origin: il widget calcola l'origin dal src del proprio <script>.
  // Permette deploy multi-domain senza hard-coding.
  const src = script.src;
  let origin = '';
  try {
    origin = new URL(src).origin;
  } catch {
    console.warn('[wiki-embed] script src non valido:', src);
    return null;
  }

  const rawPosition = (script.dataset.position ??
    'bottom-right') as (typeof POSITION_VALUES)[number];
  const position = POSITION_VALUES.includes(rawPosition) ? rawPosition : 'bottom-right';

  const color = script.dataset.color ?? '#0ea5e9';
  const label = script.dataset.label ?? 'Chat';
  const width = Math.max(280, parseInt(script.dataset.width ?? '380', 10) || 380);
  const height = Math.max(360, parseInt(script.dataset.height ?? '560', 10) || 560);

  return { token, origin, position, color, label, width, height };
}

function findScriptFallback(): HTMLScriptElement | null {
  // Fallback per ambienti dove document.currentScript è null (es.
  // moduli ES inline). Cerca lo <script> il cui src finisce con
  // /embed.js — euristica safe per il nostro caso d'uso.
  const scripts = document.getElementsByTagName('script');
  for (let i = scripts.length - 1; i >= 0; i--) {
    const s = scripts[i];
    if (s.src && /\/embed\.js(\?|$)/.test(s.src)) return s;
  }
  return null;
}

function createBubble(cfg: WidgetConfig): HTMLButtonElement {
  const btn = document.createElement('button');
  btn.type = 'button';
  btn.setAttribute('aria-label', cfg.label);
  btn.style.cssText = [
    'position:fixed',
    cfg.position === 'bottom-right' ? 'right:24px' : 'left:24px',
    'bottom:24px',
    'width:56px',
    'height:56px',
    'border-radius:50%',
    'border:none',
    `background:${cfg.color}`,
    'color:#ffffff',
    'cursor:pointer',
    'box-shadow:0 8px 24px rgba(0,0,0,0.18)',
    'display:flex',
    'align-items:center',
    'justify-content:center',
    'z-index:2147483646',
    'font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif',
    'transition:transform 150ms ease',
  ].join(';');
  btn.title = cfg.label;
  // Inline SVG icon chat-bubble (no external dep).
  const ns = 'http://www.w3.org/2000/svg';
  const svg = document.createElementNS(ns, 'svg');
  svg.setAttribute('width', '26');
  svg.setAttribute('height', '26');
  svg.setAttribute('viewBox', '0 0 24 24');
  svg.setAttribute('fill', 'none');
  svg.setAttribute('stroke', 'currentColor');
  svg.setAttribute('stroke-width', '2');
  svg.setAttribute('stroke-linecap', 'round');
  svg.setAttribute('stroke-linejoin', 'round');
  const path = document.createElementNS(ns, 'path');
  path.setAttribute(
    'd',
    'M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z'
  );
  svg.appendChild(path);
  btn.appendChild(svg);
  return btn;
}

function createIframe(cfg: WidgetConfig): HTMLIFrameElement {
  const iframe = document.createElement('iframe');
  // L'URL embed punta a una pagina ospitata dal wiki: il bundle dentro
  // l'iframe è il mini-app React generato da ``frontend/embed/``.
  iframe.src = `${cfg.origin}/embed/?token=${encodeURIComponent(cfg.token)}`;
  iframe.title = 'Chat';
  iframe.setAttribute('allow', 'clipboard-write');
  // sandbox: permettiamo script (React serve scripts) + same-origin
  // (cookie-less fetch al backend dallo stesso origine). NO allow-popups
  // → l'iframe non può aprire pagine arbitrarie sul host page.
  iframe.setAttribute('sandbox', 'allow-scripts allow-same-origin allow-forms');
  iframe.style.cssText = [
    'position:fixed',
    cfg.position === 'bottom-right' ? 'right:24px' : 'left:24px',
    'bottom:92px',
    `width:${cfg.width}px`,
    `height:${cfg.height}px`,
    'max-width:calc(100vw - 32px)',
    'max-height:calc(100vh - 120px)',
    'border:none',
    'border-radius:14px',
    'box-shadow:0 16px 48px rgba(0,0,0,0.22)',
    'background:#ffffff',
    'z-index:2147483647',
    'display:none',
  ].join(';');
  return iframe;
}

function init(): void {
  const cfg = readConfig();
  if (!cfg) return;
  if (document.querySelector('[data-wiki-embed-loaded]')) return; // idempotent

  const bubble = createBubble(cfg);
  const iframe = createIframe(cfg);
  bubble.dataset.wikiEmbedLoaded = '1';

  let open = false;
  const setOpen = (next: boolean) => {
    open = next;
    iframe.style.display = open ? 'block' : 'none';
    bubble.style.transform = open ? 'scale(0.95)' : 'scale(1)';
  };

  bubble.addEventListener('click', () => setOpen(!open));

  window.addEventListener('message', (event) => {
    // Solo messaggi dall'iframe del wiki.
    if (event.source !== iframe.contentWindow) return;
    const data = event.data as { type?: string } | null;
    if (!data || typeof data.type !== 'string') return;
    if (data.type === 'embed:close') setOpen(false);
  });

  const mount = () => {
    document.body.appendChild(iframe);
    document.body.appendChild(bubble);
  };
  if (document.body) {
    mount();
  } else {
    document.addEventListener('DOMContentLoaded', mount, { once: true });
  }
}

init();
