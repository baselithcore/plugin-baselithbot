# Report di Ricerca Pattern di Attacco Honeypot

Framework completo per la generazione di report di ricerca sulla cybersecurity di livello accademico basati sui dati honeypot. Il sistema passa dai tradizionali avvisi di rischio a osservazioni di ricerca strutturate e analitiche, adatte a ricercatori di sicurezza e analisti SOC.

## Funzionalità

### Tipi di Report

1. **Executive** - Riepilogo di alto livello per management e stakeholder
2. **Technical** - Analisi tecnica dettagliata con IOC e pattern di attacco
3. **Compliance** - Report focalizzato sulla conformità per scopi di audit
4. **Incident** - Report di risposta agli incidenti per eventi di sicurezza
5. **Pentest** - Risultati dei penetration test e vulnerabilità riscontrate
6. **Threat Intel** - Report di threat intelligence con analisi botnet e C&C

### Formati di Esportazione

- **Markdown** - Leggibile dall'uomo, compatibile con il version control e visualizzazioni ASCII
- **PDF** - Report ultra-professionali con grafici SVG, copertine e indice
- **JSON** - Accesso programmatico ai dati di ricerca

### Sezioni di Livello Ricerca (Personalizzabili)

- **Abstract & Keywords** (Riepilogo accademico potenziato da LLM)
- **Key Findings** (Osservazioni analitiche quantificate)
- **MITRE ATT&CK Mapping** (ID, Tecnica, Evidenza, Confidenza)
- **Visual Analysis** (Grafici SVG incorporati: Severità, Categorie, Geografia)
- **Temporal Analysis** (Timeline dell'intensità degli attacchi su 24h/7g)
- **Attack Pattern Analysis** (Analisi comportamentale e TTP)
- **Geographic Source Analysis** (Attribuzione e analisi dei cluster)
- **Botnet Cluster Analysis** (Punteggio di coordinamento C&C)
- **Research Methodology** (Approccio di raccolta e analisi)
- **Research Insights** (Osservazioni strategiche e direzioni future)
- **Statistical Analysis** (Metriche di distribuzione e matrici di correlazione)
- **References & Further Reading** (Citazioni accademiche e di framework)
- **Appendix** (Riepilogo dati grezzi ed esportazione IOC)
- **Detailed Payload Analysis** (Analisi dei payload raw sanitizzati per evidenziare le tecniche d'attacco)

## Guida Rapida

### 1. Generare un Report via API

```bash
# Ottieni token di accesso
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"identifier": "admin@test.com", "password": "your-password"}' \
  | jq -r '.access_token')

# Anteprima report (risposta JSON)
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/honeypot/reports/preview?report_type=technical&time_range_hours=168"

# Scarica report Markdown
curl -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -X POST http://localhost:8000/api/honeypot/reports/generate/markdown \
  -d '{
    "config": {
      "report_type": "technical",
      "format": "markdown",
      "sections": ["executive_summary", "attack_analytics", "recommendations"],
      "time_range_hours": 168,
      "classification": "INTERNAL"
    }
  }' \
  -o security_report.md

# Scarica report PDF
curl -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -X POST http://localhost:8000/api/honeypot/reports/generate/pdf \
  -d '{
    "config": {
      "report_type": "executive",
      "format": "pdf",
      "sections": ["executive_summary", "threat_landscape", "recommendations"],
      "time_range_hours": 24,
      "organization_name": "ACME Corp",
      "classification": "CONFIDENTIAL"
    }
  }' \
  -o executive_report.pdf
```

### 2. Generare via Web UI

1. Vai alla **Dashboard Honeypot** → Scheda **Reports**
2. Seleziona la configurazione del report:
   - **Honeypot**: Tutti o uno specifico honeypot
   - **Report Type**: Executive, Technical, ecc.
   - **Time Range**: Ultime 24ore, 7 giorni, 30 giorni
   - **Sections**: Seleziona quali sezioni includere
3. Clicca **Preview Report** per vedere i risultati
4. Clicca **Markdown** o **PDF** per scaricare

## Configurazione

### Report Potenziati da LLM (Opzionale)

Il sistema può utilizzare LLM (Large Language Model) per generare analisi approfondite in linguaggio naturale. Questo è **opzionale** e utilizzerà i template se non configurato.

#### Disabilitare LLM (Consigliato per Produzione/VPS)

Per report più veloci senza dipendenze esterne:

```bash
# Nel file .env
HONEYPOT_REPORTS_USE_LLM=false
```

#### Abilitare LLM con Ollama (Locale)

```bash
# Avvia Ollama
ollama serve

# Scarica un modello leggero
ollama pull llama3.2:3b

# Configura in .env
LLM_PROVIDER=ollama
LLM_MODEL=llama3.2:3b
OLLAMA_BASE_URL=http://localhost:11434
```

#### Abilitare LLM con OpenAI

**Opzione 1: Usa OpenAI per tutto (report + altri agenti)**

```bash
# Configura in .env
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-your-api-key-here
LLM_MODEL=gpt-4o-mini  # Veloce ed economico
```

**Opzione 2: Usa OpenAI SOLO per i report (consigliato per setup ibrido)**

```bash
# Usa Ollama come default per chat/agenti
LLM_PROVIDER=ollama
LLM_MODEL=llama3.2:latest
OLLAMA_BASE_URL=http://localhost:11434

# Ma usa OpenAI specificamente per i report
OPENAI_API_KEY=sk-your-api-key-here
HONEYPOT_REPORT_LLM_PROVIDER=openai
HONEYPOT_REPORT_LLM_MODEL=gpt-4o-mini
```

Questo approccio ibrido risparmia denaro usando Ollama gratuito per task di routine, ma sfrutta GPT di alta qualità per report di sicurezza importanti.

### Generazione PDF

Per la generazione PDF nativa (non fallback HTML):

```bash
pip install weasyprint markdown-it-py

# Su Ubuntu/Debian
sudo apt-get install -y \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libgdk-pixbuf2.0-0 \
    libffi-dev \
    shared-mime-info
```

## Riferimento API

### GET `/api/honeypot/reports/types`

Ottieni i tipi di report, le sezioni e i formati disponibili.

**Risposta:**

```json
{
  "types": [
    {"id": "executive", "name": "Executive", "description": "..."},
    {"id": "technical", "name": "Technical", "description": "..."}
  ],
  "sections": [
    {"id": "executive_summary", "name": "Executive Summary", "description": "..."},
    {"id": "attack_analytics", "name": "Attack Analytics", "description": "..."}
  ],
  "formats": [
    {"id": "pdf", "name": "PDF"},
    {"id": "markdown", "name": "MARKDOWN"}
  ]
}
```

### GET `/api/honeypot/reports/preview`

Genera anteprima del report senza scaricarlo.

**Parametri Query:**

- `report_type` (required): executive, technical, compliance, incident, pentest, threat_intel
- `time_range_hours` (optional, default: 168): Intervallo temporale in ore (1-720)
- `honeypot_id` (optional): Filtra per ID honeypot specifico
- `sections` (optional, repeatable): Sezioni da includere

**Esempio:**

```bash
GET /api/honeypot/reports/preview?report_type=technical&time_range_hours=24&sections=executive_summary&sections=attack_analytics
```

### POST `/api/honeypot/reports/generate`

Genera report completo (formato JSON).

**Body Richiesta:**

```json
{
  "config": {
    "report_type": "technical",
    "format": "json",
    "sections": ["executive_summary", "attack_analytics", "recommendations"],
    "time_range_hours": 168,
    "honeypot_id": "ssh-ubuntu",
    "organization_name": "ACME Security",
    "classification": "INTERNAL"
  },
  "title": "Weekly Security Assessment"
}
```

### POST `/api/honeypot/reports/generate/markdown`

Genera e scarica report Markdown.

**Body Richiesta:** Come `/generate`

**Risposta:** Download file Markdown

### POST `/api/honeypot/reports/generate/pdf`

Genera e scarica report PDF (o fallback HTML).

**Body Richiesta:** Come `/generate`

**Risposta:** Download file PDF (o HTML se weasyprint non disponibile)

## Architettura

```text
ReportService (service.py)
├── ReportDataAggregator (aggregator.py)
│   └── Recupera dati da HoneypotDAO
├── ReportTextGenerator (generator.py)
│   └── Generazione testo basata su template (fallback)
├── ModularReportLLMService (llm/service.py)
│   ├── ExecutiveSummaryGenerator
│   ├── ThreatAnalysisGenerator
│   ├── ResearchSectionGenerator (New)
│   └── Fallback handlers
├── ReportRenderer (renderer.py)
│   └── Rendering Markdown con grafici ASCII
└── Route Handlers (routes/reports.py)
    └── Generazione PDF/HTML con iniezione grafici SVG
```

## Miglioramenti PDF Professionali

Il sistema genera PDF di livello accademico includendo:

1. **Copertina**: Logo istituzione, statistiche di riepilogo e periodi di osservazione.
2. **Indice**: Navigazione strutturata per tutte le sezioni.
3. **Visualizzazioni SVG**:
   - Grafico a torta distribuzione severità
   - Grafico a barre categorie di attacco
   - Distribuzione sorgente geografica
   - Timeline attività di attacco (trend 24h)
   - Matrice di correlazione tipo attacco

## Performance e Ottimizzazione

### Basato su Template (No LLM)

- **Velocità**: ~1-2 secondi
- **Memoria**: Bassa (~100MB)
- **Dipendenze**: Nessuna
- **Qualità**: Buona, analisi basata sui fatti

### Potenziato da LLM (Ollama Locale)

- **Velocità**: ~20-40 secondi
- **Memoria**: Media (~500MB-2GB dipendendo dal modello)
- **Dipendenze**: Ollama + modello
- **Qualità**: Eccellente, insight in linguaggio naturale

### Potenziato da LLM (OpenAI)

- **Velocità**: ~5-15 secondi
- **Memoria**: Bassa (~100MB)
- **Dipendenze**: API key OpenAI
- **Qualità**: Eccellente, analisi professionale
- **Costo**: ~$0.01-0.05 per report (gpt-4o-mini)

## Risoluzione Problemi

Vedi [reports_troubleshooting.md](./reports_troubleshooting.md) per la guida dettagliata alla risoluzione problemi.

### Fix Rapidi Problemi Comuni

**Reports in timeout su VPS:**

```bash
# Disabilita LLM per report istantanei
export HONEYPOT_REPORTS_USE_LLM=false
```

**PDF restituisce HTML:**

```bash
# Installa dipendenze PDF
pip install weasyprint markdown-it-py
```

**Report vuoti:**

```bash
# Controlla se gli honeypot hanno dati
curl http://localhost:8000/api/honeypot/stats
```

## Sviluppo

### Aggiungere Nuovi Tipi di Report

1. Aggiungi enum a `reports/models.py`:

```python
class ReportType(str, Enum):
    MY_NEW_TYPE = "my_new_type"
```

1. Aggiungi sezioni di default in `routes/reports.py`:

```python
def _get_default_sections(rt: ReportType) -> List[ReportSection]:
    defaults = {
        ...
        ReportType.MY_NEW_TYPE: [
            ReportSection.EXECUTIVE_SUMMARY,
            ReportSection.CUSTOM_SECTION,
        ],
    }
```

1. Opzionalmente aggiungi prompt LLM in `reports/llm/prompts/`

### Aggiungere Nuove Sezioni Report

1. Aggiungi enum a `reports/models.py`:

```python
class ReportSection(str, Enum):
    MY_SECTION = "my_section"
```

1. Aggiungi aggregazione dati in `reports/aggregator.py`:

```python
async def build_my_section_data(self, ...) -> List[MyData]:
    # Recupera e aggrega dati
```

1. Aggiungi generazione sezione in `reports/service.py`:

```python
if ReportSection.MY_SECTION in config.sections:
    report.my_section_data = await self.aggregator.build_my_section_data(...)
```

1. Aggiungi rendering in `reports/renderer.py`:

```python
def _render_my_section(self, report: SecurityReport) -> str:
    # Converti dati in markdown
```

## Testing

```bash
# Unit test per generazione report
pytest tests/unit/test_honeypot_reports.py -v

# Integration test con dati reali
pytest tests/integration/test_reports_api.py -v

# Test servizio LLM
pytest plugins/honeypot/reports/llm/tests/ -v
```

## Considerazioni di Sicurezza

1. **Autenticazione Richiesta**: Tutti gli endpoint report richiedono autenticazione (ruolo Admin o User)
2. **Filtro Dati**: I report possono essere filtrati per honeypot_id per scenari multi-tenant
3. **Livelli Classificazione**: Supporto per PUBLIC, INTERNAL, CONFIDENTIAL, RESTRICTED
4. **Dati Sanitizzati**: I dati di attacco (payload) inclusi nei report sono sanitizzati tramite `sanitize_for_llm` prima dell'elaborazione per prevenire prompt injection.
5. **Rate Limiting**: Considera il rate limiting degli endpoint di generazione report in produzione

## Best Practices

1. **Usa intervalli temporali appropriati**: Intervalli brevi (24h-7g) per report regolari, lunghi (30g) per compliance
2. **Seleziona sezioni rilevanti**: Non includere tutte le sezioni se non necessarie
3. **Cache report**: Per intervalli accessati frequentemente, considera implementazione caching
4. **Monitora costi LLM**: Traccia utilizzo API OpenAI se usi LLM a pagamento
5. **Testa fallback**: Assicurati che la generazione basata su template funzioni quando LLM non disponibile
6. **Pianifica report**: Usa cron o task queue per generazione report automatizzata
7. **Archivia report**: Memorizza report generati per compliance e analisi storica

## Roadmap

- [ ] Pianificazione e automazione report
- [ ] Consegna via Email
- [ ] Caching report
- [ ] Template personalizzati
- [ ] Supporto multilingua
- [ ] Confronto report (diff tra periodi)
- [ ] Report HTML interattivi
- [ ] Formato esportazione Excel
- [ ] Libreria template report
