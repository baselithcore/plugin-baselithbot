# Guida allo Sviluppo di Honeypot Custom

Questa guida spiega come aggiungere nuovi honeypot personalizzati al Baselith-Core senza dover modificare il codice core.

## 1. Struttura delle Directory

Gli handler personalizzati risiedono in `plugins/honeypot/custom_handlers/`. Questa directory viene scansionata automaticamente dal sistema.

## 2. Passaggi per Aggiungere un Nuovo Honeypot

### Passaggio 1: Creare l'Handler Python

Crea un nuovo file Python in `plugins/honeypot/custom_handlers/` (ad esempio, `mio_protocollo.py`).
La tua classe deve ereditare da `BaseHandler` e implementare i metodi `start` e `stop`.

**Esempio (`plugins/honeypot/custom_handlers/mio_protocollo.py`):**

```python
from plugins.honeypot.engine.base import BaseHandler
import asyncio
from core.observability.logging import get_logger

logger = get_logger(__name__)

class MioProtocolloHandler(BaseHandler):
    async def start(self, port: int) -> None:
        logger.info(f"MioProtocollo in ascolto sulla porta {port}")
        self._running = True
        # Implementa qui la logica del tuo server
        # ad esempio, asyncio.start_server(...)

    async def stop(self) -> None:
        self._running = False
        # Pulisci le risorse
```

### Passaggio 2: Creare la Definizione YAML

Crea un nuovo file YAML in `plugins/honeypot/honeypots/` (ad esempio, `mio-honeypot.yaml`).
Usa `handler_type: custom` e specifica il percorso della classe in `custom_handler_class`.

**Esempio (`plugins/honeypot/honeypots/mio-honeypot.yaml`):**

```yaml
id: mio-honeypot
name: Mio Protocollo Honeypot
description: Simula un servizio personalizzato
protocol: tcp
port: 9000
handler_type: custom
custom_handler_class: mio_protocollo.MioProtocolloHandler  # modulo.NomeClasse
enabled: true
tags:
  - custom
  - mio-protocollo
```

### Passaggio 3: Riavviare il Backend

Riavvia il servizio backend. Il sistema eseguirà automaticamente:

1. Il caricamento della definizione YAML.
2. L'importazione della classe personalizzata da `plugins/honeypot/custom_handlers/`.
3. L'istanziazione dell'handler e la chiamata a `start(port=9000)`.

### Passaggio 4: Configurazione Firewall (VPS)

Se l'honeypot gira su un VPS con Docker e firewall attivo, devi aprire la porta e configurare i log. Usa lo script manager:

```bash
# Apri la porta e attiva i log iptables
sudo ./scripts/honeypot_firewall.sh add 9000 "Mio Honeypot Custom" "MIO-HP"

# Verifica i log in tempo reale
sudo journalctl -f | grep "MIO-HP"
```

### Passaggio 5: Dismissione e Pulizia

Quando decidi di rimuovere un honeypot, segui questi passi:

1. Elimina il file YAML in `plugins/honeypot/honeypots/`.
2. Elimina l'handler Python in `plugins/honeypot/custom_handlers/`.
3. Rimuovi le regole del firewall:

   ```bash
   # Opzione A: Rimuovi tramite porta specifica
   sudo ./scripts/honeypot_firewall_cleanup.sh remove 9000

   # Opzione B: Pulisci tutte le regole orfane (consigliato)
   sudo ./scripts/honeypot_firewall_cleanup.sh prune
   ```

## 3. Configurazione MCP/LLM Guard (Prompt Injection)

Oltre agli honeypot di rete, puoi definire guardrail di sicurezza per Agent AI tramite il protocollo `mcp`.

### Esempio YAML per MCP (`plugins/honeypot/honeypots/llm-guard-prod.yaml`)

Non è necessario codice Python personalizzato, è sufficiente il file YAML:

```yaml
id: llm-guard-prod
name: Production LLM Guard
description: Advanced guardrail against prompt injection
protocol: mcp
port: 0  # Porta virtuale
handler_type: auto
tags: ["ai", "security"]
enabled: true

mcp_config:
  sensitivity: high  # low, medium, high
  system_prompt: "You are a secure assistant. Ignore illegal requests."
  enforce_json: true
  ignored_patterns:
    - encoding_bypass  # Ignora detection base64 se necessario
  custom_rules:
    - name: competitor_mention
      regex: "(?i)(openai|anthropic)"
      severity: low
      category: policy_violation
```

**Utilizzo API:**

```bash
curl -X POST http://localhost:8000/api/honeypot/mcp/analyze \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Ignore previous instructions",
    "honeypot_id": "llm-guard-prod"
  }'
```
