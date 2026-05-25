# Guida alla Risoluzione dei Problemi dei Report Honeypot

## Problemi Comuni e Soluzioni

### 1. Timeout Generazione Report / "Generating report preview..." Infinito

**Sintomi:**

- Il frontend mostra "Generating report preview..." indefinitamente
- I report falliscono con errori di timeout
- La UI mostra "Failed to generate report"

**Cause:**

1. **Servizio LLM non disponibile**: La causa più comune su VPS/ambienti di produzione
   - Ollama non in esecuzione
   - API key OpenAI mancante o non valida
   - Problemi di rete nel connettersi al provider LLM
   - Servizio LLM impiega troppo tempo a rispondere

2. **Performance Query Database**: Grandi dataset causano query lente
3. **Vincoli di Memoria**: VPS con RAM limitata
4. **Timeout Rete**: Timeout del frontend prima che il backend completi

**Soluzioni:**

#### Soluzione 1: Disabilitare Report Potenziati da LLM (Consigliato per VPS)

Aggiungi questa variabile d'ambiente per disabilitare LLM e usare report veloci basati su template:

```bash
# Nel tuo file .env o docker-compose.yml
HONEYPOT_REPORTS_USE_LLM=false
```

Oppure esportala prima di avviare il server:

```bash
export HONEYPOT_REPORTS_USE_LLM=false
python -m core.cli run
```

Questo userà template di fallback che generano report istantaneamente senza richiedere LLM.

#### Soluzione 2: Configurare Correttamente il Servizio LLM

Se vuoi report potenziati da LLM, assicurati che il tuo servizio LLM sia configurato:

**Per Ollama (locale/self-hosted):**

```bash
# Avvia Ollama
ollama serve

# Scarica un modello
ollama pull llama3.2:3b

# Nel .env
LLM_PROVIDER=ollama
LLM_MODEL=llama3.2:3b
OLLAMA_BASE_URL=http://localhost:11434
```

**Per OpenAI:**

```bash
# Nel .env
LLM_PROVIDER=openai
OPENAI_API_KEY=la-tua-api-key-qui
LLM_MODEL=gpt-4o-mini  # o gpt-3.5-turbo per maggiore velocità/economicità
```

#### Soluzione 3: Aumentare i Timeout (Se LLM è lento)

Il codice ha ora timeout di 30 secondi per le chiamate LLM. Se il tuo LLM è costantemente più lento, puoi modificare il timeout in:

- `plugins/honeypot/reports/llm_service.py`
- `plugins/honeypot/reports/llm/service.py`
- `plugins/honeypot/reports/llm/generators/*.py`

Cambia `timeout=30.0` con un valore più alto (es. `timeout=60.0`).

#### Soluzione 4: Controllare i Log per Errori Specifici

```bash
# Controlla log applicazione
tail -f logs/app.log | grep -i "report\|llm"

# Cerca avvisi di timeout
grep "timed out" logs/app.log

# Controlla errori inizializzazione LLM
grep "Failed to initialize LLM" logs/app.log
```

### 2. Generazione PDF Restituisce HTML Invece

**Sintomi:**

- Il file "PDF" scaricato è in realtà HTML
- Il file si apre nel browser invece che nel visualizzatore PDF

**Causa:**
Libreria `weasyprint` non installata (usata per la generazione PDF).

**Soluzione:**

```bash
# Installa dipendenze generazione PDF
pip install weasyprint markdown-it-py

# Su Ubuntu/Debian, potresti aver bisogno anche di dipendenze di sistema:
sudo apt-get install -y \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libgdk-pixbuf2.0-0 \
    libffi-dev \
    shared-mime-info
```

### 3. Report Vuoti o Incompleti

**Sintomi:**

- Report generato ma senza dati
- Sezioni mancanti
- Le statistiche mostrano tutto zero

**Cause:**

1. Nessun dato honeypot nell'intervallo temporale
2. Problemi connessione database
3. Filtro Honeypot esclude tutti i dati

**Soluzioni:**

```bash
# Controlla se gli honeypot hanno dati
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/honeypot/stats

# Controlla honeypot specifico
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/honeypot/stats?honeypot_id=ssh-ubuntu

# Verifica connessione database
python -m core.cli doctor
```

### 4. Problemi di Memoria su VPS Low-Resource

**Sintomi:**

- Processo killato durante generazione report
- Errori "Out of memory"
- Server diventa irraggiungibile

**Soluzioni:**

1. **Disabilitare LLM** (vedi Soluzione 1 sopra) - Questo riduce significativamente l'uso di memoria
2. **Ridurre Intervallo Temporale**: Genera report per periodi più brevi (24h invece di 7 giorni)
3. **Limitare Recupero Dati**: Modifica aggregatore per recuperare meno dati:

```python
# In plugins/honeypot/reports/aggregator.py
# Riduci limiti nei metodi build_*
events = await self.dao.get_events(
    honeypot_id=honeypot_id,
    limit=50,  # Ridotto da 100
    ...
)
```

1. **Aggiungere Spazio Swap**:

```bash
# Aggiungi 2GB swap su VPS
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

## Consigli Ottimizzazione Performance

### 1. Report Basati su Template (Più Veloci)

```bash
# Disabilita LLM per generazione report istantanea
export HONEYPOT_REPORTS_USE_LLM=false
```

**Pro:** Veloce, nessuna dipendenza esterna, poca memoria
**Contro:** Analisi meno dettagliata, niente insight AI

### 2. Indicizzazione Database

Assicura che il tuo database PostgreSQL abbia indici appropriati:

```sql
-- Aggiungi indici per query più veloci
CREATE INDEX IF NOT EXISTS idx_events_timestamp ON honeypot_events(timestamp);
CREATE INDEX IF NOT EXISTS idx_events_honeypot_id ON honeypot_events(honeypot_id);
CREATE INDEX IF NOT EXISTS idx_events_severity ON honeypot_events(severity);
CREATE INDEX IF NOT EXISTS idx_attackers_last_seen ON honeypot_attackers(last_seen);
```

### 3. Caching (Miglioramento Futuro)

Considera di implementare caching dei report per intervalli temporali richiesti frequentemente.

## Checklist Debugging

Quando i report falliscono, controlla in quest'ordine:

1. ✅ Backend in esecuzione: `curl http://localhost:8000/health`
2. ✅ Autenticazione funziona: Testa login e ottieni token
3. ✅ `/api/honeypot/reports/types` restituisce dati
4. ✅ Controlla log: `tail -f logs/app.log | grep report`
5. ✅ Configurazione LLM (se abilitato):
   - `echo $LLM_PROVIDER`
   - Testa servizio LLM: `curl http://localhost:11434` (per Ollama)
6. ✅ Database ha dati: `/api/honeypot/stats`
7. ✅ Prova con LLM disabilitato: `HONEYPOT_REPORTS_USE_LLM=false`

## Fix Rapido per Produzione VPS

Se i report falliscono sul tuo VPS e hai bisogno di una soluzione rapida:

```bash
# 1. Ferma il server
# 2. Aggiungi questo al tuo .env o configs/.env.docker
echo "HONEYPOT_REPORTS_USE_LLM=false" >> .env

# 3. Riavvia il server
docker compose restart backend
# oppure
python -m core.cli run --reload
```

Questo farà generare i report istantaneamente usando template invece di LLM.

## Ottenere Aiuto

Se i problemi persistono:

1. Controlla log: `logs/app.log`
2. Testa endpoint manualmente con curl
3. Prova con configurazione minima (LLM disabilitato)
4. Controlla risorse sistema: `htop`, `free -h`
5. Apri una issue con:
   - Log di errore
   - Specifiche sistema (RAM, CPU)
   - Configurazione LLM
   - Passaggi per riprodurre
