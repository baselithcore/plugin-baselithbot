# Setup Ibrido LLM per Report (Ollama + OpenAI)

Guida per configurare un setup ibrido che usa:

- **Ollama (locale/gratuito)** per chat e agenti generici
- **OpenAI GPT** per funzionalità critiche honeypot:
    - Report di sicurezza (executive summaries, threat analysis)
    - Analisi AI degli attacchi singoli (AI classification)
- **Ollama (locale/gratuito)** per chat e agenti generici
- **OpenAI GPT** solo per report di sicurezza critici

## Vantaggi del Setup Ibrido

✅ **Risparmio sui costi**: GPT solo dove serve veramente
✅ **Performance**: Ollama locale = veloce per task quotidiani
✅ **Qualità**: GPT per report professionali
✅ **Resilienza**: Se OpenAI è down, Ollama continua a funzionare

## Configurazione

### 1. Setup Ollama (Base System)

```bash
# Installa Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Avvia Ollama
ollama serve

# Scarica un modello leggero
ollama pull llama3.2:latest  # 2GB, veloce
# oppure
ollama pull llama3.2:3b     # 1.5GB, più veloce
```

### 2. Setup OpenAI (Solo per Reports)

```bash
# Ottieni la API key da: https://platform.openai.com/api-keys
# Crea una nuova key con limiti di budget
```

### 3. Configura .env.prod

```bash
# ========================================
# Default LLM (Ollama) - Per tutto il resto
# ========================================
LLM_PROVIDER=ollama
LLM_MODEL=llama3.2:latest
OLLAMA_BASE_URL=http://localhost:11434

# ========================================
# OpenAI - API Key
# ========================================
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# ========================================
# Reports Override - Usa GPT per i report
# ========================================
HONEYPOT_REPORT_LLM_PROVIDER=openai
HONEYPOT_REPORT_LLM_MODEL=gpt-4o-mini
```

### 4. Deploy con Docker Compose

```bash
# Copia la configurazione
cp .env.prod.example .env.prod
# Modifica con i tuoi valori (OPENAI_API_KEY, password, etc.)
vim .env.prod

# Riavvia i servizi
docker compose down
docker compose up -d

# Verifica i log
docker compose logs -f backend | grep -i "llm\|report"
```

## Verifica della Configurazione

### Test 1: Sistema Generale usa Ollama

```bash
# Il sistema di default dovrebbe usare Ollama
docker compose logs backend | grep "LLMService"
# Output atteso: "Initialized LLMService with provider=ollama"
```

### Test 2: Report usa OpenAI

```bash
# Genera un report e controlla i log
docker compose logs backend | grep "report.*LLM"
# Output atteso: "Using report-specific LLM: openai/gpt-4o-mini"
```

### Test 3: Genera Report di Prova

```bash
# Login
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"identifier": "admin@test.com", "password": "your-pass"}' \
  | jq -r '.access_token')

# Test report preview
time curl -s -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/honeypot/reports/preview?report_type=technical&time_range_hours=24" \
  | jq -r '.executive_summary' | head -10
```

Dovresti vedere un executive summary generato da GPT (più naturale e dettagliato).

## Scelta del Modello OpenAI

### gpt-4o-mini (Consigliato) ⭐

```bash
HONEYPOT_REPORT_LLM_MODEL=gpt-4o-mini
```

- 💰 **Costo**: ~$0.01-0.03 per report
- ⚡ **Velocità**: ~5-10 secondi
- ✅ **Qualità**: Eccellente per report professionali
- 📊 **Budget**: ~$1/mese per 30 report giornalieri

### gpt-4o (Premium)

```bash
HONEYPOT_REPORT_LLM_MODEL=gpt-4o
```

- 💰 **Costo**: ~$0.05-0.10 per report
- ⚡ **Velocità**: ~10-15 secondi
- ✅ **Qualità**: Massima qualità per report esecutivi
- 📊 **Budget**: ~$3/mese per 30 report giornalieri

### gpt-3.5-turbo (Budget)

```bash
HONEYPOT_REPORT_LLM_MODEL=gpt-3.5-turbo
```

- 💰 **Costo**: ~$0.005 per report
- ⚡ **Velocità**: ~3-5 secondi
- ⚠️ **Qualità**: Buona ma meno dettagliata
- 📊 **Budget**: ~$0.15/mese per 30 report giornalieri

## Stima dei Costi Mensili

Con **gpt-4o-mini** (consigliato):

| Frequenza Report | Report/Mese | Costo Stimato |
|------------------|-------------|---------------|
| 1 al giorno      | 30          | $0.60-1.00    |
| 3 al giorno      | 90          | $1.80-2.70    |
| 1 a settimana    | 4           | $0.08-0.12    |

**Nota**: Costi molto contenuti grazie all'uso ibrido!

## Risoluzione Problemi

### Problema: Report usa Ollama invece di OpenAI

**Verifica 1**: Controlla variabili d'ambiente

```bash
docker compose exec backend env | grep HONEYPOT_REPORT
# Deve mostrare:
# HONEYPOT_REPORT_LLM_PROVIDER=openai
# HONEYPOT_REPORT_LLM_MODEL=gpt-4o-mini
```

**Verifica 2**: Controlla che OpenAI API key sia valida

```bash
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY" | jq .
```

**Soluzione**: Riavvia dopo aver configurato correttamente

```bash
docker compose down
docker compose up -d
```

### Problema: OpenAI timeout o errori

**Sintomo**: Report falliscono o vanno in timeout

**Soluzione 1**: Verifica la API key e limiti di rate

```bash
# Controlla usage su: https://platform.openai.com/usage
```

**Soluzione 2**: Fallback automatico a template

Il sistema ha già un fallback a 30 secondi. Se GPT non risponde, usa i template.

**Soluzione 3**: Disabilita temporaneamente LLM

```bash
# In .env.prod
HONEYPOT_REPORTS_USE_LLM=false

# Riavvia
docker compose restart backend
```

### Problema: Ollama non raggiungibile

**Sintomo**: Chat/agenti non funzionano

**Soluzione 1**: Verifica che Ollama sia attivo

```bash
curl http://localhost:11434/api/tags
```

**Soluzione 2**: Avvia Ollama

```bash
ollama serve
```

**Soluzione 3**: Se Ollama è in un altro container

```bash
# In .env.prod
OLLAMA_BASE_URL=http://ollama:11434  # Nome del container
```

## Best Practices

### 1. Monitora i Costi OpenAI

```bash
# Imposta limiti su: https://platform.openai.com/account/limits
# Consigliato: $5-10/mese per uso moderato
```

### 2. Usa Report Template per Testing

Durante sviluppo, disabilita LLM per report più veloci:

```bash
# In .env (development)
HONEYPOT_REPORTS_USE_LLM=false
```

### 3. Cache dei Report

Considera di implementare caching per report frequenti:

```python
# Esempio: cache report giornalieri per 12 ore
```

### 4. Scheduled Reports

Genera report automaticamente di notte per ridurre latenza:

```bash
# Cron job esempio
0 2 * * * /usr/local/bin/generate-daily-report.sh
```

## Confronto Setup

### Setup 1: Ollama Only (Gratuito)

```bash
LLM_PROVIDER=ollama
LLM_MODEL=llama3.2:latest
# Reports useranno Ollama di default
```

- ✅ Gratuito
- ✅ Privacy (tutto locale)
- ⚠️ Qualità report media
- ⚠️ Richiede GPU per performance

### Setup 2: OpenAI Only (Costoso)

```bash
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
LLM_MODEL=gpt-4o-mini
# Tutto usa OpenAI
```

- ⚠️ Costoso ($5-20/mese)
- ✅ Qualità massima ovunque
- ✅ Veloce
- ❌ Dipendenza da API esterna

### Setup 3: Ibrido (Consigliato) ⭐

```bash
LLM_PROVIDER=ollama
HONEYPOT_REPORT_LLM_PROVIDER=openai
```

- ✅ Economico (~$1-2/mese)
- ✅ Qualità alta dove serve
- ✅ Resiliente
- ✅ Il meglio dei due mondi

## Advanced: Multiple Override Patterns

Se in futuro vuoi altri override specifici:

```bash
# Chat agent usa Ollama
LLM_PROVIDER=ollama

# Reports usa GPT-4o-mini
HONEYPOT_REPORT_LLM_PROVIDER=openai
HONEYPOT_REPORT_LLM_MODEL=gpt-4o-mini

# Attack Analysis usa GPT-3.5 (più economico)
HONEYPOT_ATTACK_ANALYSIS_PROVIDER=openai
HONEYPOT_ATTACK_ANALYSIS_MODEL=gpt-3.5-turbo

# Discovery Analysis usa Claude (se supportato)
HONEYPOT_DISCOVERY_LLM_PROVIDER=anthropic
HONEYPOT_DISCOVERY_LLM_MODEL=claude-3-haiku
```

## Risorse

- [OpenAI Pricing](https://openai.com/pricing)
- [Ollama Models](https://ollama.com/library)
- [OpenAI API Limits](https://platform.openai.com/docs/guides/rate-limits)

## Supporto

In caso di problemi:

1. Verifica logs: `docker compose logs -f backend`
2. Testa connessioni: OpenAI e Ollama
3. Controlla variabili d'ambiente
4. Consulta [reports_troubleshooting.md](./reports_troubleshooting.md)
