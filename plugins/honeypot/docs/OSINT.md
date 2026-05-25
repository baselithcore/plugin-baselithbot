# 🕵️ Honeypot OSINT Enrichment Service

Il modulo **Honeypot OSINT** integra funzionalità di threat intelligence esterne per arricchire i dati raccolti dagli honeypot con reputazione IP, analisi malware e contestualizzazione delle minacce.

## 📋 Panoramica

- **Enrichment Automatico**: Arricchisce IOC (IP, Domini, URL) estratti dagli eventi di attacco.
- **Sorgenti Multiple**: Aggrega dati da URLhaus, ThreatFox, IPinfo, e (opzionalmente) AbuseIPDB/VirusTotal.
- **Stealth & Security**: Utilizza User-Agent personalizzabile (**BaselithCore**) e caching aggressivo per minimizzare l'impronta.

## ⚙️ Configurazione

Il servizio è configurabile interamente tramite variabili d'ambiente nel file `.env` o `config/plugins-honeypot.yaml`.

### 1. Attivazione

Per abilitare il servizio (disabilitato di default):

```env
HONEYPOT_OSINT_ENABLED=true
```

### 2. User-Agent Personalizzato

Per impostazione predefinita, il bot si presenta come `BaselithCore`. È possibile personalizzare il nome del prodotto per maggiore furtività o branding:

```env
# Risultato: "Mozilla/5.0 (compatible; MySecurityBot/1.0; +security-research)"
HONEYPOT_OSINT_USER_AGENT_NAME=MySecurityBot
```

Se si desidera il controllo completo sulla stringa User-Agent:

```env
HONEYPOT_OSINT_USER_AGENT="Mozilla/5.0 (compatible; CustomBot/2.1; +internal)"
```

### 3. Sorgenti Dati

Configura quali sorgenti utilizzare e le eventuali API key:

```env
# Sorgenti abilitate (lista separata da virgole in JSON array format se supportato, altrimenti default)
# Default: ["urlhaus", "threatfox", "ipinfo"]

# API Keys (Opzionali)
HONEYPOT_OSINT_ABUSEIPDB_API_KEY=vostra-chiave
HONEYPOT_OSINT_VIRUSTOTAL_API_KEY=vostra-chiave
HONEYPOT_OSINT_ALIENVAULT_API_KEY=vostra-chiave
```

### 4. Performance & Caching

Ottimizza il comportamento del scraper:

```env
# Durata cache in ore (default: 24)
HONEYPOT_OSINT_CACHE_TTL_HOURS=24

# Richieste massime al minuto globale (default: 10)
HONEYPOT_OSINT_RATE_LIMIT_PER_MINUTE=10
```

## 🏗️ Integrazione

Il servizio è integrato nel **ThreatIntelGenerator** (`plugins/honeypot/discovery/threat_intel/core.py`).
Quando viene generato un bundle di IOC dagli eventi di attacco, se l'enrichment è abilitato:

1. Estrae IP, domini e URL unici.
2. Controlla la cache locale (Redis/In-Memory).
3. Interroga le sorgenti configurate in parallelo.
4. Aggrega i punteggi di reputazione e threat level.
5. Inserisce i risultati nel campo `osint_enrichment` del bundle IOC.

### Esempio di Dati Arricchiti

```json
{
  "osint_enrichment": {
    "ip_reputations": {
      "192.168.1.5": {
        "threat_level": "high",
        "abuse_score": 85,
        "is_known_attacker": true,
        "tags": ["mirai", "botnet"],
        "country": "RU"
      }
    },
    "malicious_urls": ["http://evil.com/payload.sh"],
    "statistics": {
      "cache_hits": 5,
      "duration_seconds": 1.2
    }
  }
}
```

## 🛡️ Sicurezza Operativa

- **User-Agent Stealth**: Per le verifiche C&C (Command & Control), il sistema usa uno User-Agent stealth che imita un vero browser Chrome su Windows, diverso da quello di scraping dichiarato.
- **No Self-Scan**: Il sistema esclude automaticamente IP e domini presenti in whitelist locale.
