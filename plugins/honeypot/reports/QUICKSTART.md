# 🚀 Quick Start - LLM-Enhanced Reports

Inizia a generare report professionali in 2 minuti!

## ⚡ Setup Veloce

### Opzione 1: Ollama (Locale, Gratis) - CONSIGLIATO

```bash
# 1. Installa Ollama (se non già installato)
curl -fsSL https://ollama.ai/install.sh | sh

# 2. Scarica modello (4GB, ~2 minuti)
ollama pull llama3.2

# 3. Verifica sia attivo
curl http://localhost:11434/api/tags

# 4. Il tuo .env è già configurato! ✓
# LLM_PROVIDER=ollama
# LLM_MODEL=llama3.2:latest
# LLM_API_BASE=http://localhost:11434
```

### Opzione 2: OpenAI (Cloud, Qualità Superiore)

```bash
# 1. Hai già una API key in .env! ✓
#    HONEYPOT_ANALYSIS_LLM_API_KEY=sk-proj-b24_...

# 2. Modifica .env per usarla nei report:
nano .env

# Cambia questa riga:
LLM_PROVIDER=ollama

# In:
LLM_PROVIDER=openai
LLM_API_KEY=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

# (oppure copia la key da HONEYPOT_ANALYSIS_LLM_API_KEY)
```

## 🧪 Test Immediato

```bash
# Test completo (tutti i report types)
python -m plugins.honeypot.reports.test_llm_reports

# Test specifico
python -m plugins.honeypot.reports.test_llm_reports --test executive

# Solo template (senza LLM, per confronto)
python -m plugins.honeypot.reports.test_llm_reports --no-llm
```

**Output atteso:**

```txt
================================================================================
LLM-Enhanced Report Generation Test Suite
================================================================================
LLM Enabled: True
Provider: ollama
Model: llama3.2:latest

================================================================================
EXECUTIVE SUMMARY TEST
================================================================================

Report ID: a3f2e1c4
Generated: 2024-01-15 10:30:45
...

--- Executive Summary ---
## Executive Overview

### Security Posture Status: ELEVATED

Over the past 168 hours (7 days), Test Security Corp's security monitoring
infrastructure detected and analyzed 3,847 security events...
[continua con analisi dettagliata]
...

================================================================================
TEST SUMMARY
================================================================================
EXECUTIVE: ✓ PASSED
TECHNICAL: ✓ PASSED
THREAT_INTEL: ✓ PASSED
MARKDOWN: ✓ PASSED

Overall: ✓ ALL TESTS PASSED
================================================================================
```

## 📊 Genera il Tuo Primo Report

### Via API

```bash
# 1. Assicurati che il server sia attivo
python -m core.cli run

# 2. In un altro terminale, genera report
curl -X GET "http://localhost:8000/honeypot/reports/preview?report_type=executive&time_range_hours=168" \
  | jq '.executive_summary' -r

# 3. Scarica PDF
curl -X POST "http://localhost:8000/honeypot/reports/generate/pdf" \
  -H "Content-Type: application/json" \
  -d '{
    "config": {
      "report_type": "technical",
      "time_range_hours": 168,
      "organization_name": "Your Company"
    },
    "title": "Weekly Security Report"
  }' --output my_report.pdf

# 4. Apri il PDF
open my_report.pdf  # macOS
# xdg-open my_report.pdf  # Linux
```

### Via Python

```python
import asyncio
from plugins.honeypot.reports import (
    ReportService,
    ReportConfig,
    ReportType,
    ReportSection
)

async def main():
    # Crea service (LLM enabled by default)
    service = ReportService()

    # Configura report
    config = ReportConfig(
        report_type=ReportType.EXECUTIVE,
        time_range_hours=168,  # 7 giorni
        organization_name="Your Company",
        sections=[
            ReportSection.EXECUTIVE_SUMMARY,
            ReportSection.THREAT_LANDSCAPE,
            ReportSection.RECOMMENDATIONS,
        ]
    )

    # Genera!
    report = await service.generate_report(config=config)

    # Stampa executive summary
    print(report.executive_summary)

    # Salva come markdown
    markdown = service.render_markdown(report)
    with open("report.md", "w") as f:
        f.write(markdown)

    print("\n✓ Report salvato in report.md")

asyncio.run(main())
```

## 📈 Confronta LLM vs Template

```bash
# Genera con LLM
python -m plugins.honeypot.reports.test_llm_reports --test executive > llm_report.txt

# Genera senza LLM (template)
python -m plugins.honeypot.reports.test_llm_reports --test executive --no-llm > template_report.txt

# Confronta
diff llm_report.txt template_report.txt
```

**Differenza che vedrai:**

- Template: ~100 parole, statistiche base
- LLM: ~400-800 parole, analisi contestuale, business impact, trend, raccomandazioni specifiche

## 🎛️ Personalizza

### Cambia Temperatura (Creatività)

```bash
# .env
LLM_TEMPERATURE=0.3  # Più factual, deterministico
LLM_TEMPERATURE=0.7  # Balanced (default)
LLM_TEMPERATURE=1.0  # Più creativo
```

### Modelli Alternativi

```bash
# Ollama - Altri modelli
ollama pull mixtral:8x7b      # Migliore qualità, più lento (26GB)
ollama pull codellama:34b     # Focus tecnico (19GB)
ollama pull mistral:latest    # Alternativa a llama3.2 (4GB)

# Poi in .env:
LLM_MODEL=mixtral:8x7b
```

```bash
# OpenAI - Altri modelli
LLM_MODEL=gpt-4-turbo-preview  # Massima qualità
LLM_MODEL=gpt-4                # High quality
LLM_MODEL=gpt-3.5-turbo        # Veloce, economico
```

### Report Types Disponibili

```python
ReportType.EXECUTIVE      # Board-level, non-tecnico
ReportType.TECHNICAL      # Dettagli TTPs, MITRE ATT&CK
ReportType.THREAT_INTEL   # IOCs, attribution, campaigns
ReportType.COMPLIANCE     # Audit, logging, policies
ReportType.INCIDENT       # Timeline, root cause
ReportType.PENTEST        # Vulnerabilità, remediation
```

## 🐛 Troubleshooting

### Errore: "Connection refused"

```bash
# Ollama non attivo
ollama serve  # Avvia in background

# Oppure verifica
curl http://localhost:11434/api/tags
```

### Errore: "Model not found"

```bash
# Modello non scaricato
ollama pull llama3.2

# Lista modelli disponibili
ollama list
```

### Errore: "OpenAI API key invalid"

```bash
# Testa API key
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer sk-your-key-here"

# Verifica .env
cat .env | grep LLM_API_KEY
```

### LLM non viene usato (fallback a template)

```bash
# Controlla logs
tail -f logs/app.log | grep -i llm

# Dovresti vedere:
# INFO: ReportService initialized with LLM-enhanced generation enabled
# INFO: LLM service initialized successfully
# INFO: Generating executive summary with LLM

# Se vedi:
# WARNING: Failed to initialize LLM service
# Controlla configurazione .env
```

### Report troppo lento

```bash
# Ollama: Usa modello più piccolo
LLM_MODEL=llama3.2:latest  # Fast (4GB)

# OpenAI: Usa gpt-3.5-turbo
LLM_MODEL=gpt-3.5-turbo  # 3-5x più veloce

# Abilita caching (già attivo)
LLM_ENABLE_CACHE=true
LLM_CACHE_TTL=3600
```

## 📚 Prossimi Passi

1. **Leggi esempi dettagliati**: [`EXAMPLES.md`](EXAMPLES.md)
2. **Documentazione completa**: [`README.md`](README.md)
3. **Summary implementazione**: [`IMPLEMENTATION_SUMMARY.md`](IMPLEMENTATION_SUMMARY.md)
4. **Customizza prompts**: [`prompts.py`](prompts.py)

## 💡 Tips

- **Development**: Usa Ollama (gratis, locale)
- **Production**: Usa OpenAI gpt-4o-mini (qualità/costo ottimale)
- **Demo/Clienti**: Usa OpenAI gpt-4-turbo (massima qualità)
- **Report schedulati**: Disabilita LLM per ridurre costi (`use_llm=False`)
- **Report on-demand**: Abilita LLM per massima qualità

## 🎉 Fatto

Ora hai report professionali che competono con **CrowdStrike**, **Splunk**, e **Palo Alto Networks**!

Per supporto: Consulta [README.md](README.md) o [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md).
