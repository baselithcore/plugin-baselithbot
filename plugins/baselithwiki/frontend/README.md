# LLM Wiki — Frontend

Chat ChatGPT-style sul vault Obsidian, con streaming e citazioni wikilink.

Stack: React 19 · Vite 7 · TypeScript · Tailwind v4 (CSS-first) · framer-motion · react-markdown · lucide-react · sonner.

Design: dark-first, palette OKLCH, tipografia Inter/JetBrains Mono, mesh gradient hero, composer con border-gradient animato durante streaming.

## Setup

```bash
cd frontend
npm install
npm run dev          # http://localhost:5173
```

Il dev server fa proxy di `/api/*` verso `http://127.0.0.1:8000` (FastAPI `main.py` alla root del repo).

## Build

```bash
npm run build        # output in dist/
npm run preview
```

## Keyboard shortcuts

- `⌘K` / `Ctrl+K` → nuova conversazione
- `⌘B` / `Ctrl+B` → toggle sidebar
- `↵` → invia · `⇧↵` → nuova riga

## Architettura componenti

```text
src/
├── App.tsx                # shell completa (sidebar + main + sources drawer)
├── main.tsx, index.css    # entry, design tokens @theme
├── lib/
│   ├── types.ts           # tipi condivisi col backend
│   ├── api.ts             # fetch + streaming NDJSON
│   └── cn.ts              # tw-merge helper + uid
├── hooks/
│   ├── useChat.ts         # stato chat + streaming eventi
│   └── useAutoResize.ts   # textarea auto-grow
└── components/
    ├── Sidebar.tsx        # conversazioni + elenco pagine wiki
    ├── StatusPill.tsx     # indicatore provider/embedder/qdrant
    ├── EmptyState.tsx     # hero con prompt suggeriti
    ├── MessageList.tsx
    ├── Message.tsx        # markdown + wikilink chip + azioni hover
    ├── Composer.tsx       # textarea + graph toggle + stop button
    └── Sources.tsx        # drawer destro con preview pagina
```

## Streaming protocol

Il backend espone `/api/chat/stream` come **NDJSON** (una riga JSON per evento). Sequenza:

```json
{"type":"agent","content":"Retriever"}
{"type":"step","content":"Ricerca ibrida…"}
{"type":"hits","count":8}
{"type":"agent","content":"RAG"}
{"type":"step","content":"Generazione…"}
{"type":"token","content":"La "}
{"type":"token","content":"franchigia "}
...
{"type":"sources","items":[{"document_id":"concepts/franchigie-e-scoperti", ...}]}
{"type":"done"}
```

Compatibile col protocollo di `graphrag/agents/rag_agent.RAGAgent.answer_question_stream`.

## Wikilinks clickabili

Ogni `[[concepts/foo]]` nel markdown della risposta viene trasformato in un chip
che:

1. apre il drawer destro sulla pagina citata (preview del body markdown);
2. espone un bottone "Obsidian" che lancia `obsidian://open?vault=<name>&file=<rel>`
   (URI precomputata dal backend in `GET /api/wiki/page/{id}.obsidian_uri`; il
   nome vault deriva dal basename di `WIKI_ROOT` o dall'env `OBSIDIAN_VAULT_NAME`).

## Deploy

In produzione imposta `VITE_API_URL=https://…` e servi `dist/` dietro nginx,
puntando le rotte `/api/*` al FastAPI.
