# agent-jira · Frontend React/Vite

Console glassmorph per chat, analisi documenti e sync Jira.

## Prerequisiti

- Node.js >= 18 e npm.
- Backend FastAPI raggiungibile. Se la UI è servita dal backend, usa la stessa origin automaticamente.

## Avvio sviluppo

```bash
cd frontend
npm install
VITE_API_BASE_URL=http://localhost:8181 npm run dev
```

- Apre su `http://localhost:5173` con HMR.

## Build produzione + serving dal backend

```bash
cd frontend
npm run build
```

- Output in `app/static/frontend` (configurato in `vite.config.ts`).
- Avvia il backend (`uvicorn backend:app --reload` o `python backend.py`).
- UI pronta su `http://localhost:8181/console`.

## Config

- `VITE_API_BASE_URL`: URL dell'API backend se diverso dalla stessa origin della pagina.
- Porta dev: `5173` (override in `vite.config.ts`).

## Struttura rapida

- `src/App.tsx`: shell e tab.
- `src/components/ChatPanel.tsx`: chat + sorgenti/Jira.
- `src/components/AnalysisPanel.tsx`: upload/KB, planner, sync Jira.
- `src/components/KbPanel.tsx`: gestione documenti indicizzati, ricerca, cancellazione, statistiche Jira.
- `src/api/client.ts`: chiamate REST.
- `src/styles.css`: tema glassmorphism.

## Tipografia

- Il font di default è `Inter` (importato in `src/main.tsx` via `@fontsource/inter/*` e impostato nello stack di `src/styles.css`).
- Per tornare allo stack precedente (`Space Grotesk`, `Sora`) basta rimuovere `Inter` dalla `font-family` in `styles.css` o metterlo in coda dopo i due font: lo stack è in testa al file.
- Se non serve più `Inter`, rimuovi anche gli import da `src/main.tsx` (linee `@fontsource/inter/...`).

## Novità UI (planner/Jira)

- Card user story: chip priorità colorati, pulsante Jira compatto e badge statistiche ridotti.
- “Mostra dettagli” apre un overlay modale con ruolo/obiettivo/beneficio, scenari BDD e test case; puoi lanciare la creazione su Jira anche dal modale.
- Sidebar “Dettagli documento”: griglia meta (nome/tipo, dimensione, caratteri, percorso KB) con tag monospaziati e riepilogo in paragrafi.
- Sezione Domande aperte usa icona `?` (CircleHelp) più adatta alle FAQ.

## Knowledge Base (KB)

- **Gestione documenti**: visualizza tutti i documenti indicizzati con ricerca full-text su nome e path.
- **Cancellazione**: permette di rimuovere documenti (icona cestino) triggerando la pulizia automatica di filesystem, Qdrant e GraphDB.
- **Integrazione Jira**: mostra contatori live di User Story e Test Case collegati a ogni documento (on-demand via hover/click sull'icona info).
- **UX**: feedback visivi per copia path e azioni distruttive; layout responsive con caricamento progressivo.
