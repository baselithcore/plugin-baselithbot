# Quickstart — 5 minuti

Percorso minimo per **valutare** il motore: nessun provider esterno, nessuna autenticazione, parti da un seed e fai una domanda. Per la guida completa con auth, provider esterno, GPU/Ollama tuning e ingest reale: vedi [`getting-started.md`](getting-started.md).

## Prerequisiti

- Docker + Compose
- Python ≥ 3.10 con `uv` o `pip`
- 8 GB RAM liberi

## Tre comandi

```bash
# 1. Servizi infra (solo Qdrant, niente Postgres/Redis/auth)
docker compose up -d qdrant

# 2. Engine + extra ingest
pip install -e ".[hybrid,ingest]"

# 3. Avvia backend in setup mode (APP_DOMAIN unset → wizard prende il controllo)
python -m llm_wiki serve --reload
```

In un altro terminale:

```bash
cd frontend && npm install && npm run dev
```

## Forka un seed

Apri <http://localhost:5173>. Il wizard è bloccante in setup mode.

1. Step **Identità** → sezione "Esempi pronti" → clic **Duplica** sul seed che ti interessa (`insurance`, `legal`, `medical`, `technical`).
2. Salta autenticazione (resta opzionale in single-tenant locale).
3. Step **Provider**: scegli `ollama` se l'hai locale, altrimenti `openai` con la tua key (~5 chiamate per la sintesi prompt).
4. Step **Documenti**: salta o trascina un PDF di esempio (1 file basta).
5. **Riepilogo** → applica. Il backend si riavvia da solo, l'ingest parte in background.

## Prima domanda

Quando il pannello "Tutto pronto" mostra il bottone **Apri wiki**, click. Atterri sull'EmptyState con domande suggerite del seed. Scegline una, oppure scrivi liberamente.

Le risposte citano numericamente i passaggi (`[1]`, `[2]`, …): clic per aprire la fonte verbatim.

## Dove andare dopo

| Scenario | Doc |
| -------- | --- |
| Personalizzare prompt e tipi di pagina | [`domain-pack-spec.md`](domain-pack-spec.md) |
| Caricare i tuoi PDF in massa | [`getting-started.md`](getting-started.md#ingest) |
| Aggiungere autenticazione | [`auth-rbac.md`](auth-rbac.md) |
| Deploy in produzione | [`deployment.md`](deployment.md) |
| Editing in Obsidian | sezione *Obsidian integration* di `CLAUDE.md` |

## Reset

```bash
docker compose down -v          # azzera Qdrant
rm -rf domains/<tuo-pack>       # rimuovi il pack scaffolded
unset APP_DOMAIN WIKI_ROOT      # rimuovi env (o cancellali da .env)
```
