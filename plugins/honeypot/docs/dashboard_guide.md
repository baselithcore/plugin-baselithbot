# 🖥️ Honeypot Dashboard Guide

Questa guida descrive le funzionalità e l'interfaccia della dashboard del plugin Honeypot, accessibile tramite la Single Page Application (SPA) in `frontend/apps/honeypot`.

---

## 🧭 Navigazione Principale

La dashboard è divisa in diverse sezioni (Tab) specializzate:

### 1. 🌍 Globe (Mappa 3D)

Visualizzazione in tempo reale degli attacchi su un globo 3D.

- **Honeypot Selector**: Permette di filtrare i dati visualizzati selezionando uno specifico honeypot o vedendoli tutti.
- **Live Feed**: Lista degli ultimi eventi che scorre in tempo reale.
- **Markers**: Ogni punto sulla mappa rappresenta un attaccante unico, con dimensioni proporzionali al numero di eventi.

### 2. 📊 Analytics & Stats

Statistiche aggregate per un'analisi macroscopica del traffico.

- **Top Countries**: Classifica delle nazioni più attive, con icone delle bandiere.
- **Top Attacks**: Classifica degli IP più aggressivi.
- **Protocol Breakdown**: Distribuzione degli attacchi tra SSH, HTTP, TCP, ecc.
- **Bot vs Human**: Rapporto tra traffico automatizzato e interazioni potenzialmente umane.

### 3. 📜 List (Event Log)

Tabella dettagliata di tutti gli eventi catturati, con capacità di ricerca avanzata.

- **Filtri Dinamici**:
    - **IP Address**: Supporta la ricerca parziale (es. digitando "192.168" trovi tutti i nodi della sottorete).
    - **Country**: Ricerca per codice (es. "IT") o nome (es. "Italy").
    - **Autocomplete**: I filtri suggeriscono automaticamente valori validi basandosi sui dati caricati.
- **Paginazione**: Gestione efficiente di migliaia di eventi.

### 4. ⚠️ Threats (High Severity)

Focus esclusivo sugli eventi a severità **Critical** e **High**.

- **Payload Terminal**: Visualizzazione dei payload catturati (comandi, path HTTP) in stile terminale.
- **Dettagli Espandibili**: Ogni riga può essere espansa per vedere:
    - **Technical Evidence**: Payload completo e metadati.
    - **Related CVEs**: Vulnerabilità note correlate all'attacco.
    - **Matching Patterns**: Firme rilevate dal sistema.

### 5. 🔍 Discovery (Intelligence)

Analisi profonda dei pattern di attacco coordinati.

- **Botnet Groups**: Visualizzazione dei cluster di IP che agiscono all'unisono.
- **Zero-Day Center**: Tab dedicato ai candidate zero-day rilevati dal `ZeroDayDetector`.
- **C&C Hubs**: Identificazione dei nodi di comando e controllo basata su analisi di centralità del grafo.

### 6. 🌐 RDNS Intel

Intelligence sui domini e infrastrutture degli attaccanti.

- **Reverse DNS**: Risoluzione asincrona degli Hostname per gli IP intercettati.
- **Categorization**: Classificazione automatica (VPN, Proxy, Crawler, Hosting, Malware).
- **Importance Scoring**: Prioritizzazione basata su frequenza attacchi, reputazione ASN e tentativi di exploit.
- **Filtering**: Filtri rapidi per focalizzarsi solo su minacce ad alta priorità.

---

## 🛠️ Funzionalità Interattive

### 🤖 AI Analysis Button

In ogni modal di dettaglio dell'attacco, è presente il pulsante **"Run AI Analysis"**.

- **Cosa fa**: Invia il payload e il contesto a un agente LLM specializzato.
- **Risultato**: Restituisce un'analisi dettagliata dell'intento dell'attaccante, potenziali malware coinvolti e suggerimenti per la mitigazione.

### 🔎 Search & Autocomplete

Il sistema di ricerca è stato ottimizzato per essere fluido:

- **Debounced Search**: La ricerca parte solo dopo che l'utente ha smesso di digitare per 300ms, riducendo il carico sul server.
- **Case-Insensitive**: La ricerca per testo non distingue tra maiuscole e minuscole.
- **Fuzzy Filtering**: I risultati vengono filtrati sia lato server (per grandi dataset) che lato client (per l'autocomplete immediato).

---

## 🎨 Design System

La dashboard utilizza un tema **Cyberpunk/Dark Modern**:

- **Palette**: Nero profondo (`#0a0a0a`), Grigio antracite, e colori di stato vibranti (Rosso/Giallo per severità, Verde per successo).
- **Tipografia**: Utilizzo di font monospazio (`JetBrains Mono`) per i dati tecnici e payload.
- **Iconografia**: Basata sulla libreria `Lucide React`.
