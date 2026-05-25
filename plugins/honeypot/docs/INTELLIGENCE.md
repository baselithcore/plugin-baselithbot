# 🧠 Proactive Intelligence Module

Il modulo **Proactive Intelligence** trasforma l'honeypot da un semplice collettore passivo a un motore di analisi attivo, capace di identificare e mitigare minacce complesse come botnet, DGA e campagne APT.

## 1. JA4+ Fingerprinting

Utilizziamo lo standard **JA4+** per creare impronte digitali immutabili dei client, indipendentemente dall'IP o dallo User-Agent.

- **JA4 (TLS)**: Fingerprint della negoziazione TLS (Cipher suites, estensioni). Utile per identificare strumenti di attacco (es. Cobalt Strike, Mirai).
- **JA4H (HTTP)**: Fingerprint basato su metodi, versioni e ordine degli header HTTP.
- **JA4SSH (SSH)**: Fingerprint specifico per client SSH.

> **Integrazione**: I fingerprint JA4 sono visibili nei dettagli dell'evento e nel widget dedicato nella tab "Threats".

## 2. Behavioral Graph Intelligence

Un motore grafico avanzato (`NetworkX` + `GNN-ready embeddings`) analizza le relazioni tra attaccanti.

- **Community Detection**: Algoritmo Louvain per identificare cluster di attaccanti coordinati (botnet).
- **Threat Score**: Calcolo dinamico della pericolosità di un nodo basato su centralità, volume di attacchi e fingerprint.
- **Visualizzazione**: Il grafo "Discovery" mostra i cluster con colori diversi e i nodi ad alto rischio con bordi evidenziati.

## 3. DNS Analysis Engine & Sinkhole

Protezione avanzata contro l'infrastruttura di comando e controllo (C2).

- **DGA Detection**: Rileva domini generati algoritmicamente usando analisi dell'entropia e bigrammi.
- **Fast Flux Detection**: Identifica domini che cambiano IP rapidamente con TTL bassi.
- **NXDOMAIN Burst**: Rileva beaconing di malware che cercano domini inesistenti.
- **Sinkhole**: Un server DNS integrato intercetta le richieste verso domini malevoli noti e le reindirizza verso l'honeypot stesso, emulando il C2 per raccogliere ulteriori payload.

## 4. Threat Intel Automation (MISP)

Integrazione bidirezionale con **MISP** (Malware Information Sharing Platform).

- **IoC Export**: Esporta automaticamente IP e Hash malevoli verso MISP.
- **Enrichment**: Arricchisce gli eventi honeypot con dati di intelligence esterni (es. campagne note, gruppi APT) recuperati in tempo reale da MISP.
- **Circuit Breaker**: Protegge il core system da fallimenti della rete o sovraccarichi del server MISP.
