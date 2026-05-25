# Guida Rapida alla Configurazione

Benvenuto nel plugin Honeypot. Segui questi passi per attivare la tua prima rete di deception.

## 1. Installazione

Assicurati di avere le dipendenze necessarie:

```bash
pip install asyncssh aiohttp fastapi core
```

## 2. Configurazione Iniziale

Abilita il plugin nel file di configurazione del framework o creando un file `.env` nella root del progetto:

```env
# Abilitazione Plugin
HONEYPOT_ENABLED=true

# Configurazione HoneyDOC
HONEYPOT_ENABLE_SENSIBILITY=true
HONEYPOT_ENABLE_STEALTH=true
HONEYPOT_ENABLE_FLOW_CONTROL=true
```

## 3. Aggiungere un Honeypot Personalizzato

Crea un file YAML in `plugins/honeypot/honeypots/my-server.yaml`:

```yaml
id: my-custom-server
name: "Server Interno Documenti"
protocol: http
port: 8085
handler_type: http
http_config:
  emulated_app: generic
  server_header: "Nginx/1.18.0"
honeydoc:
  personality: "linux-internal"
  stealth_delay_ms: 80
tags: ["internal", "docs"]
```

Il sistema caricherà l'honeypot automaticamente all'avvio.

## 4. Avvio e Monitoraggio

1. **Avvia il Backend:**

   ```bash
   python backend.py
   ```

2. **Accedi alla Dashboard:**
   Apri il frontend e seleziona il tab **Honeypot**. Potrai vedere:
   - Mappa 3D in tempo reale (Globe) con persistenza degli attaccanti.
   - Vista tabellare avanzata (List) per la ricerca granulare degli eventi.
   - Analisi dei trend e dei CVE correlati.
   - Stato di salute dei singoli sensori.

## 5. Test di Funzionamento

Puoi simulare un attacco per verificare che il sistema stia loggando correttamente:

```bash
# Test HTTP
curl http://localhost:8080/wp-login.php

# Test SSH (se abilitato)
ssh root@localhost -p 2222
```

Controlla la dashboard o i log in `logs/honeypot.log` per vedere l'evento catturato e classificato.
