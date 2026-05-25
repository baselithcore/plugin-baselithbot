# 🚀 Deployment Guide - LLM Report System

## ✅ Sistema Pronto

Il sistema è stato implementato e testato con successo! Tutti i componenti sono funzionanti.

## 📋 Checklist Pre-Deployment

### 1. Verifica Sistema Base ✅

```bash
# Il sistema è già verificato e funzionante!
python -c "from plugins.honeypot.reports import ReportService; print('✅ OK')"
```

### 2. Configurazione LLM

Scegli il tuo provider:

#### Opzione A: Ollama (Locale, Gratis) - CONSIGLIATO per DEV

```bash
# 1. Installa Ollama (se non presente)
curl -fsSL https://ollama.ai/install.sh | sh

# 2. Avvia Ollama (se non già attivo)
ollama serve &

# 3. Scarica modello (4GB, ~2 minuti)
ollama pull llama3.2

# 4. Verifica
curl http://localhost:11434/api/tags | jq '.models[].name'
# Dovrebbe mostrare: llama3.2:latest

# 5. Il tuo .env è GIÀ configurato per Ollama! ✅
```

#### Opzione B: OpenAI (Cloud, Alta Qualità) - CONSIGLIATO per PRODUCTION

```bash
# Hai GIÀ una API key configurata in .env! ✅
# HONEYPOT_ANALYSIS_LLM_API_KEY=sk-proj-b24_...

# Per usare OpenAI nei report, modifica .env:
nano .env

# Cambia questa riga:
# LLM_PROVIDER=ollama

# In:
# LLM_PROVIDER=openai
# LLM_MODEL=gpt-4o-mini
# LLM_API_KEY=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

# Oppure copia la key da HONEYPOT_ANALYSIS_LLM_API_KEY
```

### 3. Test del Sistema

```bash
# Test rapido (30 secondi)
python -m plugins.honeypot.reports.test_llm_reports --test executive

# Test completo (2-3 minuti)
python -m plugins.honeypot.reports.test_llm_reports

# Test con provider specifico
python -m plugins.honeypot.reports.test_llm_reports --provider openai

# Test senza LLM (fallback)
python -m plugins.honeypot.reports.test_llm_reports --no-llm
```

**Output atteso:**

```text
✓ EXECUTIVE: PASSED
✓ TECHNICAL: PASSED
✓ THREAT_INTEL: PASSED
✓ MARKDOWN: PASSED

Overall: ✓ ALL TESTS PASSED
```

### 4. Avvio Applicazione

```bash
# Avvia il server
python -m core.cli run --reload

# In un altro terminale, testa l'API
curl "http://localhost:8000/honeypot/reports/preview?report_type=executive&time_range_hours=24"
```

## 🎯 Scenari di Deployment

### Scenario 1: Development (Locale, Gratis)

**Configurazione `.env`:**

```bash
LLM_PROVIDER=ollama
LLM_MODEL=llama3.2:latest
LLM_API_BASE=http://localhost:11434
LLM_TEMPERATURE=0.7
HONEYPOT_REPORTS_USE_LLM=true
```

**Pro:**

- ✅ Gratis
- ✅ Privacy (tutto locale)
- ✅ Nessun rate limit
- ✅ Funziona offline

**Contro:**

- ❌ Richiede GPU/CPU potente
- ❌ Qualità inferiore a GPT-4
- ❌ Più lento (3-10s per section)

**Setup:**

```bash
ollama pull llama3.2
python -m core.cli run
```

---

### Scenario 2: Production (Cloud, Qualità)

**Configurazione `.env`:**

```bash
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o-mini
LLM_API_KEY=sk-proj-b24_...
LLM_TEMPERATURE=0.7
HONEYPOT_REPORTS_USE_LLM=true
```

**Pro:**

- ✅ Massima qualità
- ✅ Veloce (1-3s per section)
- ✅ Nessun requisito hardware
- ✅ Sempre disponibile

**Contro:**

- ❌ Costo (ma minimo: ~$0.001-0.003/report con gpt-4o-mini)
- ❌ Rate limits (gestiti automaticamente)
- ❌ Richiede connessione internet

**Costi stimati:**

- gpt-4o-mini: ~$0.001-0.003 per report
- gpt-4-turbo: ~$0.01-0.02 per report
- 100 report/mese con gpt-4o-mini: ~$0.10-0.30/mese

**Setup:**

```bash
# API key già presente in .env
python -m core.cli run
```

---

### Scenario 3: Hybrid (Development + Production)

**Configurazione `.env`:**

```bash
# Core system usa Ollama (gratis)
LLM_PROVIDER=ollama
LLM_MODEL=llama3.2:latest

# Report usano OpenAI (qualità) - opzionale
# LLM_REPORTS_PROVIDER=openai
# LLM_REPORTS_MODEL=gpt-4o-mini
# LLM_REPORTS_API_KEY=sk-proj-b24_...
```

**Pro:**

- ✅ Bilanciamento costi/qualità
- ✅ Ollama per task generici
- ✅ OpenAI per report importanti

**Setup:**
Implementazione futura (feature opzionale)

---

### Scenario 4: High-Volume (Template-Based)

**Configurazione `.env`:**

```bash
# Disabilita LLM per report ad alto volume
HONEYPOT_REPORTS_USE_LLM=false
```

**Quando usare:**

- Report schedulati (hourly/daily)
- Dashboard real-time
- Monitoring automatico
- Budget limitato

**Setup:**

```python
# Nel codice
service = ReportService(use_llm=False)
```

---

## 📊 Monitoring e Logging

### Verifica LLM Attivo

```bash
# Controlla logs
tail -f logs/app.log | grep -i "llm"

# Dovresti vedere:
# INFO: ReportService initialized with LLM-enhanced generation enabled
# INFO: LLM service initialized successfully
# INFO: Generating executive summary with LLM
```

### Verifica Fallback

```bash
# Se vedi questo, LLM ha fallito (ok, fallback attivo):
# WARNING: LLM executive summary failed, falling back to template
# INFO: Generating executive summary with templates
```

### Metrics da Monitorare

1. **LLM Success Rate**: % report generati con LLM vs template
2. **Response Time**: Tempo generazione per report type
3. **Cost (OpenAI)**: Token usage e costi mensili
4. **Cache Hit Rate**: % richieste servite da cache

---

## 🔧 Tuning e Ottimizzazione

### Temperature Control

```bash
# .env
LLM_TEMPERATURE=0.3  # Più factual, deterministico (compliance, audit)
LLM_TEMPERATURE=0.7  # Balanced (default, raccomandato)
LLM_TEMPERATURE=1.0  # Più creativo (executive briefings)
```

### Caching

```bash
# .env - Già configurato ottimamente
LLM_ENABLE_CACHE=true
LLM_CACHE_TTL=3600         # 1 ora (adjust per frequenza report)
LLM_CACHE_MAX_SIZE=1000    # Max cached items
```

### Model Selection

**Ollama:**

```bash
# Fast & Light (4GB VRAM)
ollama pull llama3.2           # Default, raccomandato

# High Quality (26GB VRAM)
ollama pull mixtral:8x7b       # Migliore qualità

# Technical Focus (19GB VRAM)
ollama pull codellama:34b      # Focus su analisi tecnica

# Alternative
ollama pull mistral:latest     # Buon bilanciamento
```

**OpenAI:**

```bash
# .env
LLM_MODEL=gpt-4o-mini          # Cost-effective, veloce (RACCOMANDATO)
LLM_MODEL=gpt-4-turbo-preview  # Massima qualità
LLM_MODEL=gpt-3.5-turbo        # Ultra veloce, economico
```

---

## 🐛 Troubleshooting

### Problema: "Connection refused" (Ollama)

```bash
# Soluzione: Avvia Ollama
ollama serve &

# Verifica
curl http://localhost:11434/api/tags
```

### Problema: "Model not found"

```bash
# Soluzione: Scarica modello
ollama pull llama3.2

# Lista modelli disponibili
ollama list
```

### Problema: "OpenAI API key invalid"

```bash
# Verifica key
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $LLM_API_KEY"

# Controlla .env
grep LLM_API_KEY .env
```

### Problema: LLM non viene usato

```bash
# Check 1: Logs
tail -f logs/app.log | grep -i "llm"

# Check 2: Configurazione
grep HONEYPOT_REPORTS .env
# Deve essere: HONEYPOT_REPORTS_USE_LLM=true

# Check 3: Provider attivo
# Ollama: curl http://localhost:11434/api/tags
# OpenAI: curl https://api.openai.com/v1/models -H "Authorization: Bearer sk-..."
```

### Problema: Report troppo lento

```bash
# Soluzione 1: Ollama - Usa modello più piccolo
LLM_MODEL=llama3.2:latest  # 4GB, veloce

# Soluzione 2: OpenAI - Usa modello veloce
LLM_MODEL=gpt-3.5-turbo    # 3-5x più veloce

# Soluzione 3: Disabilita per report high-volume
HONEYPOT_REPORTS_USE_LLM=false  # Solo template
```

### Problema: Costi OpenAI troppo alti

```bash
# Soluzione 1: Usa gpt-4o-mini invece di gpt-4
LLM_MODEL=gpt-4o-mini  # 10x più economico

# Soluzione 2: Aumenta cache TTL
LLM_CACHE_TTL=7200  # 2 ore invece di 1

# Soluzione 3: Disabilita per report automatici
# Nel codice:
service = ReportService(use_llm=False)  # Per scheduled reports
service_vip = ReportService(use_llm=True)  # Per on-demand reports
```

---

## 🎯 Best Practices

### Development

1. ✅ Usa Ollama (gratis)
2. ✅ Test frequenti con suite completa
3. ✅ Sperimenta con temperature e prompts

### Staging

1. ✅ Usa OpenAI gpt-4o-mini
2. ✅ Test con dati realistici
3. ✅ Misura response times e costs

### Production

1. ✅ Usa OpenAI gpt-4o-mini per costi ottimali
2. ✅ Monitor cache hit rate (target: >50%)
3. ✅ Alert su LLM failures (se >5% fallback rate)
4. ✅ Budget limits configurati
5. ✅ Fallback sempre abilitato

### Security

1. ✅ API keys in .env (mai committate)
2. ✅ .env in .gitignore
3. ✅ Rotate keys periodicamente
4. ✅ Monitor usage anomalies

---

## 📈 Scaling

### High Volume (>1000 reports/day)

```bash
# 1. Disabilita LLM per report automatici
HONEYPOT_REPORTS_USE_LLM=false

# 2. Abilita solo per on-demand (API parameter)
curl -X POST "/honeypot/reports/generate" \
  -d '{"config": {"use_llm": true}}'  # Solo quando richiesto

# 3. Implementa queue system
# - Report batch processing
# - Off-peak generation
# - Priority queues
```

### Multi-Tenant

```python
# Per tenant configuration
tenant_configs = {
    "enterprise": {"use_llm": True, "model": "gpt-4-turbo"},
    "standard": {"use_llm": True, "model": "gpt-4o-mini"},
    "basic": {"use_llm": False},  # Template only
}
```

---

## ✅ Post-Deployment Checklist

- [ ] LLM provider configurato e testato
- [ ] Test suite completato con successo
- [ ] API endpoints testati
- [ ] Logs monitoring configurato
- [ ] Fallback verificato funzionante
- [ ] Caching abilitato e configurato
- [ ] Budget limits impostati (se OpenAI)
- [ ] Documentazione letta dal team
- [ ] Backup configurazioni
- [ ] Alert configurati (opzionale)

---

## 📚 Risorse

- **Documentazione Completa**: [README.md](README.md)
- **Quick Start (2 min)**: [QUICKSTART.md](QUICKSTART.md)
- **Esempi Output**: [EXAMPLES.md](EXAMPLES.md)
- **Dettagli Tecnici**: [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md)
- **Test Suite**: `python -m plugins.honeypot.reports.test_llm_reports --help`

---

## 🎉 Sistema Pronto

Il tuo sistema di report è **production-ready**:

- ✅ Testato e funzionante
- ✅ Documentato completamente
- ✅ Configurabile facilmente
- ✅ Fallback robusto
- ✅ Pronto per scale

**Prossimo step**: Genera il tuo primo report professionale! 🚀

```bash
python -m plugins.honeypot.reports.test_llm_reports
```
