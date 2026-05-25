# 🎭 Advanced Deception System (ADS)

Il modulo **Advanced Deception System (ADS)** trasforma il plugin Honeypot da una trappola statica in una piattaforma di inganno adattiva e persistente.

Questo sistema si basa su tre pilastri fondamentali:

1. **Sophisticated Emulation**: Simulazione stateful ad alta fedeltà.
2. **ML-Powered Predictive Analytics**: Previsione delle mosse dell'attaccante.
3. **Cluster Persistence**: Sincronizzazione dello stato su nodi multipli.

---

## 1. Sophisticated Emulation

L'emulazione sofisticata sostituisce le risposte statiche con un ambiente interattivo che mantiene lo stato della sessione.

### Componenti Chiave

- **StatefulEmulator**: Il cuore del sistema. Mantiene il contesto della sessione (variabili d'ambiente, CWD, history) e gestisce le transizioni di stato.
- **FingerprintEngine**: Genera risposte che rispecchiano fedelmente il sistema operativo emulato.
- **FS & Env Mutations**: Traccia le modifiche al filesystem virtuale (VFS) e alle variabili d'ambiente per mantenerle coerenti.
- **LatencyModeler**: Simula latenze realistiche basate sul tipo di operazione (es. operazioni crypto più lente di `ls`) e si adatta alla velocità dell'attaccante.

### Profili OS Supportati

- `linux_ubuntu` (Ubuntu 22.04 LTS)
- `linux_centos` (CentOS Stream 9)
- `windows_server` (Windows Server 2022)

Ogni profilo definisce banner SSH, header HTTP, opzioni TCP/IP e comportamenti tipici.

### Esempio di Utilizzo

```python
from plugins.honeypot.emulation import StatefulEmulator, FingerprintProfile

# Carica profilo
profile = FingerprintProfile.load("linux_ubuntu")

# Inizializza emulatore
emulator = StatefulEmulator(
    session_id="session-123",
    fingerprint_profile=profile
)

# Processa comandi
response = await emulator.process_command("cat /etc/os-release")
print(response.output)  # Output Ubuntu 22.04 reale
```

---

## 2. ML-Powered Predictive Analytics

Il modulo ML analizza il comportamento dell'attaccante in tempo reale per prevedere le prossime mosse e generare "esche" (bait) su misura.

### Features

- **TTP Prediction**: Classificatore Random Forest che predice la prossima tecnica MITRE ATT&CK.
- **Feature Extraction**: Estrae 40+ metriche dalla sessione (n-grammi comandi, timing, ricognizione, complessità payload).
- **Adaptive Response**: Genera contenuti dinamici (file, credenziali) basati sulle predizioni.

### Flusso di Lavoro

1. L'attaccante esegue comandi.
2. `FeatureExtractor` analizza la sequenza.
3. `TTPPredictor` predice l'intento (es. `CREDENTIAL_DUMPING`).
4. `AdaptiveResponseGenerator` piazza un'esca appropriata (es. `/root/.ssh/id_rsa`).

### Configurazione

```yaml
ml:
  enabled: true
  prediction_threshold: 0.7
  enable_timing_features: true
```

---

## 3. Cluster Persistence

Permette di scalare l'honeypot su più nodi mantenendo la coerenza dell'inganno durante il movimento laterale.

### Funzionalità

- **Redis-backed Sync**: Sincronizzazione stato sessione sub-millisecondo via Redis Pub/Sub.
- **Lateral Movement Tracking**: Rileva quando un attaccante usa credenziali rubate su un altro nodo.
- **VFS Replication**: Le modifiche al filesystem (es. upload malware) vengono replicate su tutti i nodi clusterizzati.

### Architettura

```mermaid
graph LR
    Honeypot_A[Nodo A (Ubuntu)] -- Sync --> Redis[(Redis Cluster)]
    Honeypot_B[Nodo B (CentOS)] -- Sync --> Redis
    
    Attacker -- SSH --> Honeypot_A
    Honeypot_A -- "Malware Upload" --> Redis
    Redis -- "Replicate File" --> Honeypot_B
    
    Attacker -- "Lateral Move" --> Honeypot_B
    Honeypot_B -- "File Exists!" --> Attacker
```

---

## Configurazione Completa

Aggiungi queste sezioni al tuo `plugins.yaml` o `config.yaml`:

```yaml
honeypot:
  # ... confi esistente ...

  emulation:
    enabled: true
    default_os_profile: "linux_ubuntu"
    enable_latency_simulation: true
    
  ml:
    enabled: false # Abilita dopo il training iniziale
    training_enabled: true
    
  cluster:
    enabled: false
    redis_url: "redis://localhost:6379/0"
```
