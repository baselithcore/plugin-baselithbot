# Sistema di Notifica Webhook

Il plugin Honeypot include un robusto sistema di notifiche basato su eventi, progettato per avvisare gli amministratori in tempo reale degli attacchi ad alta gravità. Supporta molteplici provider, riduzione intelligente del rumore e pattern di resilienza.

## Funzionalità

- **Supporto Multi-Provider**:
    - **Telegram**: Messaggi formattati in Markdown con emoji e dettagli del payload.
    - **Discord**: Embed ricchi con codici colore basati sulla gravità.
    - **Webhook Generico**: Payload JSON per integrazione con strumenti SOAR (n8n, Tines, Zapier).

- **Filtro Intelligente**:
    - **Soglia di Gravità**: Avvisa solo per eventi di gravità `HIGH` e `CRITICAL`.
    - **Riduzione del Rumore**: Ignora automaticamente i tentativi di brute-force "a basso valore" comuni (es. `admin:password`, `root:root`).
    - **Esclusione Categorie**: Gli eventi `credential_harvesting` sono esclusi di default per prevenire la "notification fatigue".

- **Resilienza**:
    - **Logica di Retry**: Backoff esponenziale per le consegne fallite.
    - **Circuit Breaker**: Disabilita temporaneamente un provider dopo 5 fallimenti consecutivi.
    - **Rate Limiting**: Cooldown di 30 secondi per indirizzo IP sorgente.

## Configurazione

Configura il sistema di notifica nel tuo `plugins.yaml` o tramite variabili d'ambiente.

### Variabili d'Ambiente

```bash
HONEYPOT_ENABLE_NOTIFICATIONS=true
HONEYPOT_NOTIFICATION_MIN_SEVERITY=high
HONEYPOT_TELEGRAM_BOT_TOKEN=123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
HONEYPOT_TELEGRAM_CHAT_ID=-100123456789
HONEYPOT_DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
```

### plugins.yaml

```yaml
honeypot:
  enable_notifications: true
  notification_min_severity: "high"
  notification_cooldown_seconds: 30
  
  # Provider
  telegram_bot_token: "IL_TUO_BOT_TOKEN"
  telegram_chat_id: "IL_TUO_CHAT_ID"
  discord_webhook_url: "IL_TUO_WEBHOOK_URL"
  
  # Riduzione del Rumore
  notification_ignore_credentials:
    - "admin:password"
    - "admin:123456"
    - "root:root"
  notification_ignore_categories:
    - "credential_harvesting"
```

## Architettura

Il sistema è costruito sul `NotificationManager` che si sottoscrive all'**EventBus** centrale.

1. **Ingestione Eventi**: Ascolta `honeypot.attack.detected`.
2. **Filtraggio**:
    - Verifica la soglia di gravità.
    - Verifica se la categoria è in `notification_ignore_categories`.
    - Verifica se le credenziali corrispondono a `notification_ignore_credentials`.
3. **Rate Limiting**: Controlla la cache in-memory per notifiche recenti dallo stesso IP sorgente.
4. **Formattazione**: Converte l'`AttackEvent` nei formati specifici del provider (`TelegramFormatter`, `DiscordFormatter`).
5. **Invio (Dispatch)**: Invia le notifiche in modo asincrono con logica di retry.

## Guida all'Uso

### Configurazione Telegram

1. Crea un bot usando [@BotFather](https://t.me/BotFather).
2. Ottieni il **Token** (es. `12345:ABC...`).
3. Aggiungi il bot a un gruppo o chat.
4. Ottieni il **Chat ID** (es. usa `@get_id_bot`).
5. Configura `telegram_bot_token` e `telegram_chat_id`.

### Configurazione Discord

1. Vai su Impostazioni Server -> Integrazioni -> Webhooks.
2. Crea un nuovo Webhook.
3. Copia l'**URL del Webhook**.
4. Configura `discord_webhook_url`.

### Payload Webhook Generico

Per integrazioni personalizzate, il provider Generico invia una POST JSON:

```json
{
  "event_id": "evt_12345",
  "honeypot_id": "ssh-server",
  "severity": "critical",
  "category": "command_injection",
  "source_ip": "192.168.1.100",
  "detected_patterns": ["rm -rf", "wget"],
  "payload": "; rm -rf /",
  "timestamp": "2026-01-14T20:00:00"
}
```

## Risoluzione Problemi

- **Nessuna Notifica?**
    - Controlla che `enable_notifications` sia true.
    - Controlla i log per "NotificationManager initialized".
    - Verifica che la gravità sia almeno `HIGH`.
    - Controlla `notification_ignore_credentials` se stai testando con password comuni.

- **Troppe Notifiche?**
    - Aumenta `notification_cooldown_seconds`.
    - Aggiungi categorie specifiche a `notification_ignore_categories`.
