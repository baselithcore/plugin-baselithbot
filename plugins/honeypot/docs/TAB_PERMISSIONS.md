# Permessi dei Tab Honeypot

Questa guida spiega come limitare l'accesso a specifici tab di Honeypot per gli utenti con ruolo Guest.

## 1. Concetto

Gli utenti con il ruolo `guest` possono essere limitati a visualizzare solo un sottoinsieme dei tab disponibili. Questo è utile per fornire una visibilità limitata (ad esempio, solo la vista semplificata Monitor o Globe) senza esporre dettagli sensibili o controlli avanzati.

## 2. Tab Disponibili

Sono disponibili i seguenti identificatori di tab:

| ID Tab | Descrizione |
|--------|-------------|
| `monitor` | Monitor degli attacchi in tempo reale (Vista semplificata) |
| `globe` | Mappa degli attacchi 3D |
| `list` | Elenco tabellare degli attacchi |
| `analytics` | Statistiche dettagliate e grafici |
| `threats` | Intelligence sulle minacce e pattern |
| `pentest` | Strumenti di pentesting (**Sensibile**) |
| `discovery` | Network discovery (**Sensibile**) |

## 3. Creazione di un Utente Guest Limitato

Usa l'utility `scripts/create_user.py` dalla root del progetto per creare un utente con il ruolo `guest` e il flag `--allowed-tabs`.

### Sintassi del Comando

```bash
python scripts/create_user.py --email <EMAIL> --role guest --allowed-tabs <TABS>
```

### Esempio Pratico

Per creare un utente guest che può vedere solo la **Mappa (Globe)** e il **Monitor**:

```bash
python scripts/create_user.py \
  --email ospite@esempio.it \
  --role guest \
  --allowed-tabs monitor,globe
```

### Dettagli dei Parametri

* `--email` (`-e`): L'indirizzo email dell'utente.
* `--role` (`-r`): Deve essere impostato su `guest`.
* `--allowed-tabs`: Lista dei tab consentiti separati da virgola (senza spazi).
* `--password` (`-p`): Opzionale. Se omesso, verrà richiesta interattivamente per maggiore sicurezza.

## 4. Verifica dell'Accesso

1. Accedi con il nuovo account guest.
2. Naviga nel plugin Honeypot.
3. La barra di navigazione mostrerà **esclusivamente** i tab autorizzati.
4. Tentativi di accesso manuale ad altri URL di tab verranno reindirizzati automaticamente al primo tab disponibile.
