# Documentazione Sicurezza - Plugin Honeypot

## Panoramica

La sicurezza del plugin Honeypot è progettata seguendo il principio della **Difesa in Profondità (Defense in Depth)**. Poiché il plugin interagisce direttamente con input non attendibili provenienti da potenziali attaccanti, sono state implementate diverse barriere per prevenire che un exploit possa compromettere il framework core o l'infrastruttura sottostante.

Il sistema è stato recentemente potenziato con un layer dedicato di **LLM Guardrails** per neutralizzare attacchi avanzati.

---

## 1. LLM Guardrails

Il sistema implementa una catena di protezione a quattro livelli (`llm_guardrails.py`) che agisce prima, durante e dopo ogni invocazione dell'LLM.

### 🛡️ Hardened System Prompts

Le istruzioni di sistema per SSH e HTTP sono immutabili e includono un preambolo di sicurezza "hardcoded".

- **Non-overridable**: Il prompt di sistema viene concatenato in modo da avere sempre l'ultima parola (o la prima, a seconda della strategia di gerarchia).
- **Integrità**: Include direttive esplicite per non rivelare mai la propria natura di honeypot, indipendentemente dalle pressioni conversazionali.

### ⚖️ Instruction Hierarchy

Implementa un sistema di priorità per pesare i prompt:

1. **SYSTEM**: Massima priorità (istruzioni di sicurezza).
2. **FRAMEWORK**: Regole del core framework.
3. **PLUGIN**: Logica specifica dell'honeypot.
4. **USER**: Input dell'attaccante (priorità minima).

Ogni tentativo dell'utente di dichiarare "I am the administrator" o "Ignore previous instructions" viene rilevato dal classificatore di gerarchia e neutralizzato.

### 🔍 Output Filtering (Regex + Semantic)

Tutte le risposte generate dall'LLM passano attraverso un filtro d'uscita dinamico:

- **Regex Filter**: Identifica e maschera API keys, credenziali, path di sistema (`/etc/passwd`), e pattern di leak del system prompt.
- **Semantic Filter**: Blocca frasi che confermano indirettamente la natura di "trap" o "honeypot" attraverso un'analisi basata su blocklist semantica.

### 🚫 Refusal Policy

Se il rischio di injection calcolato (`calculate_injection_score`) supera una soglia critica (default: 0.7), il sistema interrompe l'invocazione dell'LLM e restituisce una **Refusal Response** predefinita.

- La risposta è progettata per essere "grigia" e non informativa, scoraggiando l'attaccante senza rivelare i criteri di rilevamento.

---

## 2. Protezione da Prompt Injection (Legacy & Integration)

Oltre ai nuovi Guardrails, rimangono attive le misure di base:

- **Sanitizzazione via `sanitize_for_llm`**: Tutti gli input dell'attaccante vengono passati attraverso una funzione di sanitizzazione nel modulo `security.py`.
- **Injection Scoring**: Ogni richiesta riceve un punteggio di rischio da 0.0 a 1.0 basato su oltre 40 pattern noti (DAN, jailbreak, roleplay).
- **Delimitatori Rigidi**: Gli input sono isolati tramite tag come `[ATTACKER_INPUT]` per prevenire la confusione dei token.

---

## 3. Sanitizzazione dei Dati (Event & Logs)

- **Log Isolation**: Gli input vengono ripuliti da caratteri di controllo per prevenire il log forging.
- **EventBus Safety**: Prima di emettere un `AttackEvent`, i dati vengono sanitizzati tramite `sanitize_for_event`.
- **Report Security**: I payload di attacco estratti per la reportistica sono sanitizzati con `sanitize_for_llm` per prevenire la manipolazione del contesto dell'LLM (Prompt Injection).
- **Pentest Integration**: I payload usati nei pentest sono essi stessi sanitizzati per evitare "nested injection" nel sistema di test.

---

## 4. Sicurezza della Persistenza

- **SQL Injection**: Uso esclusivo di query parametrizzate in `persistence/`.
- **Encryption**: I segreti e le chiavi di configurazione sono gestiti tramite variabili d'ambiente (Pydantic Settings), mai hardcoded.

---

## 5. Audit & Testing

- **Security Audit Script**: `scripts/security_audit_honeypot.py` per verifiche statiche.
- **Pentest Agent**: Utilizzo del modulo pentest interno per testare la propria resilienza con playbook di "Multi-turn injection" e "Tool misuse".
- **Bandit/Ruff**: Linting di sicurezza integrato nella CI/CD.

---

## Best Practices per Sviluppatori

1. **Mai invocare l'LLM direttamente**: Usa sempre `LLMSecurityLayer` o i responder esistenti.
2. **Rispetta la Gerarchia**: Non forzare mai input utente in posizioni che potrebbero avere priorità superiore alle istruzioni di sicurezza.
3. **Audit prima del merge**: Esegui un pentest completo se modifichi i guardrail o i filtri di output.

---

## 6. Architettura Isolata in Produzione

A partire dalla versione `v3` del deployment di produzione, il sistema Honeypot adotta un'architettura a **Monade Isolata** per garantire che nessun attaccante possa uscire dal perimetro dell'honeypot verso i dati reali o l'infrastruttura backend.

### 🔒 Isolamento di Rete

- **Rete `honeypot_net`**: Una rete Docker interna (`internal: true`) completamente separata dal backend. L'honeypot non può "vedere" Redis o altri servizi sensibili.
- **Exposure Selettiva**: Solo le porte target dell'attacco (es. 2222, 3000) sono esposte esternamente.

### 🔒 Isolamento dei Dati

- **Database Dedicato**: L'honeypot utilizza il database PostgreSQL `agent_analytics` dedicato, separato dai dati dell'applicazione.
- **Volume `honeypot_data`**: È l'unico volume scrivibile aggiuntivo oltre a `/tmp`. Questo volume isola i dati temporanei dagli altri container.
- **Model Isolation**: Anche la cache dei modelli (`hf_cache`) è isolata per prevenire attacchi di *Model Poisoning*.

### 🔒 Configurazione Minimale

Per deployment con risorse limitate, l'istanza Honeypot può essere configurata con:

- **`HF_HUB_OFFLINE=1`**: Utilizza i modelli pre-bakeati nell'immagine senza cercare aggiornamenti online.
- **`QDRANT_MODE=embedded`**: Utilizza un database vettoriale locale in-memory invece di connettersi a un cluster esterno.
- **`CACHE_BACKEND=local`**: Gestione della cache interna senza dipendenza da Redis.

### 🔒 Hardening del Container

- **`read_only: true`**: Filesystem di sistema in sola lettura; solo `/tmp` è scrivibile.
- **`cap_drop: ALL`**: Rimozione di tutte le capacità Linux.
- **`no-new-privileges: true`**: Prevenzione dell'escalation dei privilegi.

---

## 7. Sicurezza API

Gli endpoint API dell'Honeypot (`/api/honeypot/*`) sono protetti per prevenire l'accesso non autorizzato ai dati degli attacchi e alle funzioni di controllo:

- **Autenticazione Obbligatoria**: Tutte le rotte richiedono un token JWT valido.
- **Controllo dei Ruoli**: L'accesso è limitato agli utenti con ruolo `admin` o `user`.
- **Protezione Storage-Agnostic**: La sicurezza è applicata indipendentemente dal backend di storage (PostgreSQL, Redis, ecc.).
