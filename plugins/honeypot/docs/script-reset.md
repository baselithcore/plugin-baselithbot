# Script di Reset e Manutenzione

Il plugin Honeypot include una serie di script di utilità per gestire, pulire e resettare i dati memorizzati nei vari database (PostgreSQL, Qdrant, FalkorDB). Questi script sono situati nella directory `scripts/` alla radice del progetto.

> [!WARNING]
> Questi script sono distruttivi. Verranno eliminati permanentemente i dati dai database specificati. Usali con estrema cautela, specialmente in ambienti di produzione.

## Script Disponibili

### 1. `reset_all.py`

È lo script principale che coordina il reset di tutti i componenti.

- **Cosa fa**: Pulisce i dati di analytics dal database PostgreSQL (`agent_analytics`), Qdrant (Vector Store) e FalkorDB (Graph Store).

- **Uso**:

  ```bash
  python scripts/reset_all.py
  ```

### 2. `reset_honeypot.py`

Resetta specificamente i dati di sessione e gli eventi del plugin Honeypot, senza toccare il resto del sistema (vettori o grafi).

- **Cosa fa**: Esegue il `TRUNCATE` delle tabelle `honeypot_events` e `honeypot_sessions` in PostgreSQL.
- **Parametri**:
    - `--skip-confirm`: Salta la richiesta di conferma manuale.

- **Uso**:

  ```bash
  python scripts/reset_honeypot.py
  ```

### 3. `reset_qdrant.py`

Pulisce il Vector Store utilizzato per l'analisi dei pattern e le correlazioni CVE.

- **Cosa fa**: Elimina le collezioni specificate in Qdrant (es. `honeypot_events_vectors`).
- **Uso**:

  ```bash
  python scripts/reset_qdrant.py
  ```

### 4. `reset_graphdb.py`

Resetta il Graph Database (FalkorDB/RedisGraph).

- **Cosa fa**: Elimina tutti i nodi e le relazioni relativi agli attacchi e agli IP registrati nel grafo.
- **Uso**:

  ```bash
  python scripts/reset_graphdb.py
  ```

---

## Misure di Sicurezza

Tutti gli script di reset implementano le seguenti misure di sicurezza:

1. **Conferma Utente**: Prima di procedere, viene richiesta una conferma esplicita ("Sei sicuro? [y/N]").
2. **Supporto Dry-Run**: È possibile simulare l'operazione per verificare quali dati verrebbero eliminati.
3. **Log Dettagliati**: Ogni operazione viene registrata per permettere il monitoraggio delle attività di manutenzione.

## Esempio di Utilizzo Tipico

Se desideri ricominciare una sessione di test pulita eliminando solo gli eventi di analytics:

```bash
python scripts/reset_analytics_db.py --force
```

Se desideri resettare l'intero ecosistema honeypot:

```bash
python scripts/reset_all.py
```
