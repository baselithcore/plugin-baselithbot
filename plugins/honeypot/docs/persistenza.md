# Persistenza dei Dati Honeypot (Analytics)

Questo documento descrive lo strato di persistenza del plugin Honeypot, incaricato di memorizzare sessioni, eventi e statistiche di attacco nel database PostgreSQL dedicato (`agent_analytics`).

## Panoramica

Lo strato di persistenza è stato modulato per garantire scalabilità e manutenibilità, seguendo le linee guida del framework. Gestisce autonomamente il proprio pool di connessioni per evitare interferenze con il core del sistema.

### Struttura del Package (`plugins/honeypot/persistence/`)

Il sistema è diviso in moduli specializzati:

1. **`database.py`**: Gestisce il pool di connessioni (`psycopg_pool.AsyncConnectionPool`) e la comunicazione base con PostgreSQL.
2. **`schema.py`**: Definisce e inizializza le tabelle all'avvio del plugin.
3. **`events.py`**: Logica per il salvataggio e il recupero degli eventi di attacco (`AttackEvent`).
4. **`sessions.py`**: Logica per la gestione del ciclo di vita delle sessioni degli attaccanti (`HoneypotSession`).
5. **`retention.py`**: [NUOVO] Gestione delle policy di conservazione dati (retention per età e per numero di righe).
6. **`timeseries.py`**: [NUOVO] Motore di aggregazione temporale per grafici (hourly, daily, weekly).
7. **`aggregations.py`**: [NUOVO] Query avanzate per top attackers, heatmap di attacco e trend CVE.
8. **`stats.py`**: Motore di aggregazione per le statistiche legacy visualizzate nella dashboard.

---

## HoneypotDAO (Facade)

Per mantenere la compatibilità con il resto del plugin, viene utilizzata la classe facade `HoneypotDAO` (definita in `__init__.py`). Tutti i componenti esterni interagiscono esclusivamente con questa interfaccia.

### Metodi Principali

| Metodo                      | Descrizione                                                                                                           |
| :-------------------------- | :-------------------------------------------------------------------------------------------------------------------- |
| `ensure_schema()`           | Inizializza il database e crea le tabelle se mancanti.                                                                |
| `save_event(event)`         | Salva un singolo evento (sincrono legacy).                                                                            |
| `save_event_batched(event)` | **Raccomandato**: Aggiunge l'evento al batcher per un salvataggio ultra-performante.                                  |
| `get_events(...)`           | Recupera eventi filtrati e paginati. Supporta **partial string matching** (`LIKE/ILIKE`) per `source_ip` e `country`. |
| `save_session(session)`     | Salva o aggiorna (upsert) una sessione di attacco.                                                                    |
| `get_sessions(...)`         | Recupera le sessioni registrate.                                                                                      |
| `get_stats()`               | Calcola statistiche aggregate.                                                                                        |
| `optimize_for_scale()`      | Configura indici compositi e tabelle di archiviazione per scalare a 100K+ eventi.                                     |
| `archive_old_events(days)`  | Sposta i dati vecchi in una tabella di archivio dedicata.                                                             |
| `get_table_stats()`         | Restituisce metriche su dimensioni e volume dei dati.                                                                 |
| `apply_retention_policy()`  | [NUOVO] Applica manualmente le policy di purging basate sui limiti configurati.                                       |
| `get_retention_status()`    | [NUOVO] Restituisce lo stato attuale della retention (righe rimosse, età massima).                                    |
| `get_timeseries(...)`       | [NUOVO] Recupera dati aggregati temporalmente per dashboard.                                                          |
| `get_trends(...)`           | [NUOVO] Calcola la velocità di attacco e i trend protocol-shift.                                                      |
| `get_top_attackers(...)`    | [NUOVO] Identifica gli IP più attivi con enrichment geografico.                                                       |
| `get_attack_heatmap(...)`   | [NUOVO] Genera la matrice categoria x ora per i grafici di densità.                                                   |
| `get_cve_trends(...)`       | [NUOVO] Analisi temporale delle correlazioni CVE rilevate.                                                            |

---

## Ottimizzazione per Alte Prestazioni (Extreme Scalability)

Il plugin implementa una pipeline di persistenza aggressiva per gestire carichi elevati (>1000 eventi/secondo):

1. **Event Batching**: Gli eventi non vengono salvati singolarmente (1 INSERT per evento), ma raggruppati in batch di **50 eventi** o ogni **50ms**. Questo riduce il carico sul database del 90-95%.
2. **Connection Pooling Scalabile**: Il pool di connessioni dedicato scala fino a **50 connessioni** simultanee con timeout estesi a 60s per gestire picchi di traffico.
3. **Indici Compositi**: Vengono creati indici specializzati per query pattern frequenti (es. `source_ip + timestamp`, `severity + timestamp`) per mantenere le performance costanti anche con milioni di record.
4. **Automated Retention**: Supporto integrato per pulizia automatica basata su età (es. 30 giorni) o numero di record, prevenendo l'esaurimento del disco.
5. **Time-Series Aggregation**: Query ottimizzate che utilizzano indici temporali per aggregazioni lampo su milioni di record, alimentando i grafici della UI senza latenza.
6. **Async Processing**: Gli aggiornamenti delle sessioni e la gestione della retention sono eseguiti come background tasks non-bloccanti.

---

## Schema del Database

Il database `agent_analytics` contiene due tabelle principali:

### 1. `honeypot_sessions`

Memorizza i metadati delle sessioni di attacco.

- `session_id`: Identificativo unico della sessione.
- `source_ip`: IP dell'attaccante.
- `protocol`: Protocollo colpito (SSH, HTTP).
- `auth_success`: Indica se l'attaccante ha superato l'emulazione dell'autenticazione.
- `ai_summary`: Riassunto generato dall'AI sull'attività dell'attaccante.

### 2. `honeypot_events`

Memorizza ogni singola azione compiuta dall'attaccante.

- `event_id`: Identificativo unico dell'evento.
- `event_type`: Tipo di evento (es. comando impartito, richiesta HTTP).
- `command` / `path`: Dettagli specifici dell'azione.
- `severity`: Livello di criticità assegnato dal Captor.
- `matched_cves`: Lista di CVE correlate all'attacco.

---

## Configurazione

Il plugin utilizza PostgreSQL come unico backend di storage.

### Requisiti

- `POSTGRES_ENABLED=true` nel file `.env`
- Database `agent_analytics` creato automaticamente all'avvio

### Indici e Performance

Tutte le colonne critiche per le query (`source_ip`, `timestamp`, `session_id`, `severity`, `country_code` tramite JSONB index) sono ottimizzate per garantire tempi di risposta rapidi anche con milioni di eventi. Il filtro per nazione utilizza il campo `meta->'geo'->>'country_code'`.
