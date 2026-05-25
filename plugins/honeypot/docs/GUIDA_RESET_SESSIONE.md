# Guida al Reset e Avvio Sessione Pulita - Honeypot Plugin

Questa guida spiega come resettare completamente o parzialmente i dati del plugin Honeypot per avviare una nuova sessione di monitoraggio "pulita".

## 1. Panoramica Script di Reset

Nella cartella `scripts/` alla radice del progetto, troverai gli script necessari per pulire i vari datastore utilizzati dal sistema.

| Script | Descrizione | Datastore Interessati |
|--------|-------------|-----------------------|
| `reset_all.py` | **Reset Completo**. Pulisce tutto. | PostgreSQL, Qdrant, GraphDB |
| `reset_analytics_db.py` | Pulisce solo gli eventi e le sessioni. | PostgreSQL (Analytics) |
| `reset_qdrant.py` | Pulisce solo la memoria vettoriale. | Qdrant |
| `reset_graphdb.py` | Pulisce solo il grafo delle relazioni. | GraphDB (FalkorDB) |

---

## 2. Come Avviare una Sessione Pulita (Consigliato)

Per garantire che non ci siano residui di test precedenti o vecchi dati, segui questi passaggi:

### Passo 1: Esegui il Reset Completo

Dalla radice del progetto, esegui:

```bash
python scripts/reset_all.py
```

Il sistema ti chiederà una conferma di sicurezza.
Digita: `DELETE ALL` e premi Invio.

**Nota**: Se vuoi eseguire il reset in uno script automatizzato senza interazione, usa:

```bash
python scripts/reset_all.py --skip-confirm
```

### Passo 2: Riavvio dei Servizi (Opzionale ma Consigliato)

Se stai usando Docker (es. in produzione), segui questa sequenza per assicurarti che i database siano pronti prima del reset:

#### Sequenza Docker Compose (Consigliata)

1. **Ferma tutto**:
   `docker-compose -f docker-compose-prod-v2.yml down`
2. **Avvia solo i Database**:
   `docker-compose -f docker-compose-prod-v2.yml up -d postgres redis qdrant falkordb`
3. **Attendi 10 secondi** per l'inizializzazione dei DB.
4. **Esegui il Reset** (Esegui all'interno del container per avere le dipendenze):
   `docker-compose -f docker-compose-prod-v2.yml run --rm api python scripts/reset_all.py`
5. **Avvia l'intero sistema**:
   `docker-compose -f docker-compose-prod-v2.yml up -d`

#### Metodo diretto (se i container sono già attivi)

Se il sistema è già attivo e vuoi resettare al volo:

```bash
docker exec -it baselith-core-api python scripts/reset_all.py
```

### Passo 3: Verifica Frontend

1. Ricarica la pagina del browser (F5).
2. Vai nella tab **Analytics** o **Globe**. Dovresti vedere i contatori a zero e nessuna attività precedente.

---

## 3. Reset Parziale

Se vuoi mantenere, ad esempio, la conoscenza vettoriale (Qdrant) ma cancellare gli eventi visualizzati (PostgreSQL):

```bash
python scripts/reset_analytics_db.py
```

*Richiede conferma interattiva digitando "yes".*

---

## 4. Risoluzione Problemi Comuni

- **Errore di connessione al DB**: Assicurati che i container Docker (Postgres, Qdrant, Redis) siano attivi.
- **`ModuleNotFoundError`**: Assicurati di eseguire gli script dalla **radice del progetto** (non da dentro la cartella `scripts/`), in modo che Python possa risolvere correttemente i path dei moduli `core`.
    - ✅ Corretto: `python scripts/reset_all.py`
    - ❌ Sbagliato: `cd scripts && python reset_all.py`
