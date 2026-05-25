# 🍯 Plugin Honeypot

Honeypot potenziato dall'IA per il rilevamento degli attacchi e la correlazione dei CVE, integrato con BaselithCore.

## 📋 Panoramica

Il plugin Honeypot fornisce:

- **HoneyDOC Architecture**: Integrazione completa dei principi HoneyDOC per Sensibility, Stealth e Countermeasures.
- **YAML Honeypot Registry**: Definisci nuovi honeypot semplicemente aggiungendo file YAML in `honeypots/`.
- **SSH Honeypot**: Server SSH falso con risposte ai comandi generate da LLM e ritardi realistici.
- **HTTP Honeypot**: Emulazione di applicazioni web (WordPress, phpMyAdmin, Jenkins) con header mascherati.
- **TCP Honeypot**: Listener di porte generico per FTP, Telnet, SMTP, Redis, ecc.
- **MCP Honeypot**: Rilevamento di prompt injection LLM per proteggere gli agenti. Completamente configurabile via YAML.
- **Sensibility & Flow Control**: Classificazione fine del traffico (DROP, FORWARD, REDIRECT) ispirata a Snort.
- **Stealth Integrato**: Jitter nelle risposte e fingerprinting coerente per prevenire il rilevamento.
- **Countermeasures attive**: Contenimento del traffico outbound per prevenire abusi (HIH isolation).
- **Correlazione CVE & MITRE**: Collegamento in tempo reale tra attacchi e vulnerabilità note tramite **CVE Hunter**, arricchito con mapping **MITRE ATT&CK**.
- **Critical Alerting**: Notifiche proattive per la scoperta di CVE critici con attivazione automatica di posture difensive.
- **Feedback Loop & Learning**: Sistema di feedback per confermare le correlazioni e migliorare l'accuratezza tramite apprendimento continuo.
- **Extreme Scalability**: Capace di gestire **100K+ eventi** con latenza <1ms tramite batching (50 ev / 50ms), pooling esteso (50 connessioni) e indici compositi ottimizzati.
- **Dashboard Avanzata**: Interfaccia cyberpunk con monitoraggio in tempo reale e analisi geografica.
- **Pentesting Agent (Red Team)**: Red teaming allo stato dell'arte con **Evolutionary Fuzzing** (genetic mutations) e **Multi-Turn Attack Chains** (social engineering).
- **Proactive Intelligence Module**: Suite avanzata per la threat intelligence [📖 Dettagli](docs/INTELLIGENCE.md):
    - **JA4+ Fingerprinting**: Fingerpriting TLS/HTTP/SSH di nuova generazione per l'identificazione precisa degli attori.
    - **Behavioral Graph**: Analisi grafica con clustering (Louvain) e calcolo Threat Score per identificare botnet e C&C.
    - **RDNS Intelligence**: Risoluzione Reverse DNS asincrona con classificazione infrastruttura (VPN, Hosting, Crawler) e scoring di importanza.
    - **DNS Sinkhole**: Intercettazione e monitoraggio attivo di domini malevoli (DGA, Fast Flux).
    - **Threat Intel Automation**: Integrazione bidirezionale con MISP per export e enrichment IoC.

## 🚀 Novità UI 2.0 (Intelligence Console)

L'interfaccia è stata evoluta in una vera Console di Intelligence:

1. **Threats Tab**: Nuovi widget **JA4 Analysis** e **DNS Anomalies** per il rilevamento pattern-based.
2. **Discovery Graph**: Nodi colorati per community cluster e bordi rossi per alto Threat Score.
3. **Sinkhole Monitor**: Tab dedicata per visualizzare i domini intercettati e le vittime protette.
4. **Rich Details**: Modal di dettaglio arricchiti con dati OSINT, Geolocalizzazione e punteggi di rischio.

## 🎭 Novità ADS (Advanced Deception System)

La versione 3.0 introduce l'**Advanced Deception System**, trasformando l'honeypot in una piattaforma adattiva:

1. **Sophisticated Emulation**: Emulazione stateful fedele (Ubuntu, CentOS, Windows) con gestione coerente di filesystem, processi e latenza realistica.
2. **ML-Powered Analytics**: Predizione in tempo reale delle mosse dell'attaccante (TTP Prediction) e generazione dinamica di esche (Adaptive Baiting).
3. **Cluster Persistence**: Sincronizzazione dello stato su nodi distribuiti per tracciare il movimento laterale e mantenere la coerenza dell'inganno.

[📖 Leggi la documentazione completa ADS](docs/ADVANCED_DECEPTION.md)

## 🏭 IoT/OT Deception Layer (v3.5)

Il plugin ora supporta protocolli industriali e IoT nativi per rilevare attacchi alle infrastrutture critiche:

1. **Modbus TCP**: Emulazione PLC con registri holding e coil configurabili. Rileva scansioni e tentativi di manipolazione.
2. **MQTT Broker**: Broker IoT simulato (Mosquitto-style) con credential trapping e topic monitoring ($SYS, firmware, cmd).
3. **S7comm (Siemens)**: Emulazione avanzata S7-300/400 con supporto SZL (CPU ID) e rilevamento attacchi Stuxnet-class (DB write).

[📖 Leggi la documentazione IoT/OT](docs/IOT_OT_HONEYPOTS.md)

## 📊 Advanced Analytics & Persistence

Nuovo strato di lettura e analisi per gestire grandi volumi di dati di attacco:

1. **Time-Series Engine**: Aggregazione temporale (ora/giorno/settimana) per trend velocity e protocol distribution.
2. **Attack Heatmaps**: Visualizzazione densità attacchi (categoria x ora) per identificare picchi di attività.
3. **Automated Retention**: Policy di auto-purging basate su età (days) o volume (rows) per mantenere il DB performante.
4. **Top Attackers & CVE Trends**: Dashboard arricchita con gli attori più pericolosi e i trend delle vulnerabilità sfruttate.

[📖 Leggi la documentazione sulla Persistenza](docs/persistenza.md)

## 🛡️ Sicurezza & Deployment (Secure DNAT)

> [!IMPORTANT]
> Dalla versione 3.0, l'honeypot **NON espone più le porte via Docker** per motivi di sicurezza (Docker Proxy Bypass).

Per esporre gli honeypot in produzione, DEVI utilizzare lo script di gestione firewall che configura **IPTables DNAT**:

```bash
# Sincronizza le regole di forwarding per le porte configurate (es. 2222, 3000)
sudo ./scripts/honeypot_firewall.sh sync
```

[📖 Leggi la guida al Firewall e UFW](docs/ufw-setup.md)

## 🚀 Utilizzo

### 1. Installazione Dipendenze

Il plugin richiede `asyncssh`, `aiohttp`, `dnslib` e `community` (opzionale per Graph AI).

```bash
pip install asyncssh aiohttp fastapi dnslib python-louvain networkx pymisp
```

### 2. Configurazione Intelligence

Abilita i moduli avanzati nel tuo `plugins.yaml`:

```yaml
honeypot:
  enabled: true
  
  # Proactive Intelligence
  enable_ja4_fingerprinting: true
  enable_dns_sinkhole: true
  sinkhole_ip: "127.0.0.1"
  
  # Threat Intel
  misp_enabled: true
  misp_url: "https://misp.local"
  misp_key: "YOUR_KEY"
```

### 3. Configurazione Advanced Deception System (ADS)

Il plugin ora include un sistema di inganno avanzato con 3 pilastri:

**Variabili d'Ambiente (vedi `.env.prod.example` per la lista completa):**

```bash
# Emulation - Stateful OS emulation
HONEYPOT_EMULATION_ENABLED=true
HONEYPOT_EMULATION_DEFAULT_OS_PROFILE=linux_ubuntu

# ML - TTP Prediction & Adaptive Baiting
HONEYPOT_ML_ENABLED=true
HONEYPOT_ML_MODEL_PATH=data/models/ttp_predictor_baseline.joblib

# Cluster - Multi-node state sync via FalkorDB
HONEYPOT_CLUSTER_ENABLED=true
HONEYPOT_CLUSTER_REDIS_URL=redis://falkordb:6379/0
```

**Features Attive:**

- ✅ Persistenza filesystem tra comandi
- ✅ Rilevamento automatico 20+ TTP MITRE ATT&CK
- ✅ Predizione ML delle prossime mosse attaccante
- ✅ Generazione dinamica esche basate su predictions
- ✅ Sincronizzazione stato multi-nodo per lateral movement

[📖 Documentazione Completa ADS](docs/ADVANCED_DECEPTION.md)

[... Resto della documentazione esistente ...]
