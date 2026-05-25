# Guida Utente

Manuale d'uso end-user dell'applicazione web. Per setup amministrativo → [`getting-started.md`](getting-started.md).

## Primo accesso

Dopo che l'amministratore ha completato il setup, ricevi:

- **URL** dell'istanza (es. `https://wiki.tua-azienda.com`)
- **Email** registrata
- **Token di invito** monouso (link tipo `https://.../?invite=<token>`) **oppure** una password temporanea

### Tramite invito

1. Apri il link `https://wiki.tua-azienda.com/?invite=<token>`.
2. Inserisci nome visualizzato e password (min 12 caratteri, almeno 1 cifra + 1 maiuscola).
3. Conferma → vieni loggato automaticamente.
4. Il token è single-use: condividerlo non funziona dopo l'attivazione.

### Tramite credenziali

1. Apri l'URL → schermata di login.
2. Email + password temporanea.
3. Al primo login l'app forza il cambio password (`ForcePasswordChange`).

## Anatomia dell'interfaccia

```txt
┌─────────────────────────────────────────────────────────────┐
│  ☰  [Logo]   Edizione: [▼ Tutte]            ⌘/  ⚙️  👤      │  ← topbar
├──────────────┬──────────────────────────────────────────────┤
│              │                                               │
│  Sidebar     │   Conversazione attiva                        │
│              │                                               │
│  Nuova chat  │   ▸ "Quali sono i requisiti..."              │
│              │   ◂ "I requisiti previsti dall'art. 5...      │
│  Recenti:    │      [[normative/decreto-2024]]              │
│  • Conv. 1   │      [👍 👎]                                   │
│  • Conv. 2   │                                               │
│  • ...       │                                               │
│              │                                               │
│  📎 Carica   │   ┌─────────────────────────────┐            │
│  📚 Memorie  │   │ Scrivi un messaggio...      │            │
│              │   └─────────────────────────────┘            │
│              │   ↩ Cmd+Enter per inviare                    │
└──────────────┴──────────────────────────────────────────────┘
                                                     ↳ drawer Sources →
```

### Sidebar

- **Nuova chat** — apre conversazione vergine
- **Recenti** — lista cronologica delle tue conversazioni (cliccabile, rinominabile, cancellabile)
- **Carica PDF** — disponibile se hai permesso `ingest.run`
- **Memorie** — apre il modale gestione memorie personali

### Topbar

- **☰** — toggle sidebar
- **Edizione** (se il pack ha grouping) — filtro contesto, es. "Edizione 2024" / "Edizione 2025"
- **⌘/** — apre Command Palette (vedi sotto)
- **⚙️** — settings (tema, suggerimenti, opzioni avanzate)
- **👤** — menu utente: profilo, cambio password, logout, "Logout da tutti i device"

## Chat

### Inviare una domanda

1. Scrivi nel composer in basso.
2. Premi `Cmd+Enter` (o `Ctrl+Enter` su Linux/Windows).
3. La risposta arriva in **streaming** (vedi parole apparire in tempo reale).
4. A streaming completato compaiono:
   - **Citazioni inline** `[[cartella/slug]]` cliccabili.
   - **Drawer Sources** a destra (apri con `Cmd+S` o click su una citazione).
   - **Pulsanti feedback** 👍 👎 sotto il messaggio.

### Citazioni

Ogni claim della risposta dovrebbe essere ancorato a una fonte. Le citazioni sono link cliccabili:

- Click → apre il drawer Sources con il documento evidenziato
- Hover → preview del titolo della fonte
- Numero in pedice → indice nell'elenco fonti

> Se vedi una risposta **senza citazioni**, l'engine non ha trovato fonti rilevanti. Probabilmente la wiki non copre il tema; segnalalo all'admin (`Carica PDF` con materiale autoritativo).

### Drawer Sources

Mostra:

- Titolo del documento
- Cartella (`page_type`)
- Score di rilevanza
- Estratto del passaggio usato
- Link "Apri pagina completa" (apre `wiki/<folder>/<slug>` rendered)

Scorciatoie:

- `Cmd+S` — toggle drawer
- `Esc` — chiudi

### Feedback

Click su 👍/👎:

- Salvato in audit trail (anonimo solo per voci aggregate).
- Aiuta l'admin a identificare query problematiche.
- Opzionalmente compila il campo "perché?" per dettagli.

### Multi-turn (conversazioni)

Le tue domande sono raggruppate in **conversazioni** salvate sul tuo account.

- Ogni conversazione mantiene la storia: il modello vede gli ultimi N turni come contesto.
- Cambio conversazione → reset del contesto (nuova "memoria di lavoro").
- Click destro / hover su una conversazione in sidebar → rinomina, elimina, esporta.

### Edizioni / Grouping

Se il pack ha definito gruppi (es. annate normative), il selettore in topbar limita il retrieval a quel sottoinsieme. Esempio per Wiki Legale:

```txt
Edizione: [▼ 2024 ▼]
```

→ tutte le risposte useranno solo i documenti taggati `edizione: 2024` nel frontmatter.

## Memorie personali

Spazio privato dove salvi fatti riutilizzabili nelle tue chat (preferenze, contesto del tuo lavoro). Le memorie sono **isolate per utente** (RLS): nessun altro le vede o le usa.

### Creare una memoria

`📚 Memorie` → `+ Nuova` → testo libero. Esempio:

```txt
Lavoro nel reparto compliance, mi interessano principalmente
i decreti del 2024. Quando rispondi, dai priorità a quel periodo.
```

Salvataggio → l'embedding viene calcolato in background e indicizzato in pgvector.

### Come vengono usate

Ad ogni tua query, il motore cerca le tue memorie più rilevanti (top-K configurabile) e le inietta nel contesto, **separate dalle fonti wiki**:

```txt
[Wiki sources]
- documento ...

[User memories]
- "Lavoro nel reparto compliance..."
```

Il modello usa entrambe per rispondere; le fonti wiki vanno citate, le memorie no (sono context personale).

### Cercare / cancellare

- **Cerca**: digita una query → similarità vettoriale sulle tue memorie.
- **Cancella**: click sull'icona cestino → rimozione permanente.

> Le memorie non sono backup-ate per default lato utente. L'admin ha responsabilità del backup DB complessivo.

## Caricare PDF

Disponibile se hai `ingest.run` (ruolo `editor`+ o equivalente).

1. Sidebar → **Carica PDF**.
2. Drag & drop o file picker.
3. Modale mostra il job in tempo reale con stage (extract → classify → plan → generate → lint → critic → write).
4. Al termine: una nuova pagina wiki è disponibile per RAG, oppure file `.needs-review.md` da correggere a mano.

Errori comuni:

- "PDF non testuale" → file scansionato senza OCR. Esegui OCR esterno prima dell'upload.
- "Linter failed" → il documento non si mappa bene alle page-type del pack. Apri il `.needs-review.md` o segnala all'admin.

## Command Palette (⌘/)

Apri con `Cmd+/` (o `Ctrl+/`). Mostra tutte le azioni disponibili al tuo ruolo:

| Comando             | Scorciatoia | Note                           |
| ------------------- | ----------- | ------------------------------ |
| Nuova conversazione | `Cmd+N`     | —                              |
| Cerca tra le chat   | `Cmd+K`     | full-text su titoli e messaggi |
| Apri/chiudi sidebar | `Cmd+B`     | —                              |
| Apri/chiudi sources | `Cmd+S`     | drawer destro                  |
| Carica PDF          | —           | richiede `ingest.run`          |
| Memorie             | —           | tua collezione                 |
| Impostazioni        | `Cmd+,`     | tema, lingua                   |
| Aiuto               | `?`         | scorciatoie + guida rapida     |
| Invita utente       | —           | richiede `admin.user.manage`   |
| Gestisci ruoli      | —           | richiede `admin.user.manage`   |
| Logout              | —           | revoca refresh corrente        |
| Logout da tutti     | —           | revoca tutti i refresh         |

## Impostazioni

`⚙️` → modale settings:

- **Tema** — chiaro / scuro / sistema (persistito in localStorage)
- **Lingua UI** — sovrascrive default del pack (it / en)
- **Streaming** — on/off (off = aspetta risposta completa)
- **Mostra punteggio fonti** — debug
- **Suggerimenti starter** — abilita le card all'inizio della chat vuota

## Cambio password

`👤` → "Cambia password":

- Vecchia password (verifica)
- Nuova password (min 12 char, 1 cifra, 1 maiuscola)
- Conferma

Successo → tutti i refresh token sono **revocati eccetto il corrente** (per sicurezza). Su altri device dovrai re-loginarti.

## Sicurezza pratica

- **Logout da tutti i device** se sospetti uso non autorizzato.
- **Non condividere link di invito** già usati: sono single-use.
- L'app **non memorizza la password in nessun momento**, neanche temporaneamente lato browser.
- Il refresh token in cookie è `httpOnly` → nessun JS dell'app può leggerlo (anche se l'app fosse compromessa).

## Best practice query

✅ **Buone query**:

- Specifiche e domain-bound: "Quali sono i termini di prescrizione per..."
- Citazione di articolo / numero: "Che cosa dice l'art. 5 del decreto X?"
- Ricerca comparativa: "Differenze tra polizza A e B"

❌ **Da evitare**:

- Domande generaliste fuori dal dominio ("Che tempo fa?") → l'engine ti reindirizza alle fonti
- Query ultra-corte ("articolo 5") → molto ambigue, retrieval povero
- Catene multi-domanda nella stessa query → spezzale in turni separati

## Limitazioni note

- Risposte basate **solo** su fonti caricate dall'admin (`raw/`). Se manca, manca.
- Citazioni vengono validate: rispose con fonti hallucinate → l'engine può rifiutarsi (config `CITATION_STRICT_GROUNDING`).
- Storia conversazione viene troncata oltre N turni (config server). Per contesto lungo, salva i punti chiave come **memorie personali**.
- File caricati restano in `raw/` finché un admin non li rimuove.

## Privacy

Cosa l'app sa di te:

| Dato                       | Visibilità        | Cancellabile                 |
| -------------------------- | ----------------- | ---------------------------- |
| Email + display name       | Te + admin        | Sì (su richiesta admin GDPR) |
| Conversazioni + messaggi   | Solo te (RLS)     | Sì (delete dalla sidebar)    |
| Memorie personali          | Solo te (RLS)     | Sì (modal memorie)           |
| Feedback (👍 👎)             | Aggregato + audit | Anonymizzato a richiesta     |
| Audit eventi (login, ecc.) | Admin             | Anonimizzato non cancellato  |

Il vault wiki (`wiki/<folder>/`) è **condiviso fra tutti gli utenti del pack**: domande e contenuti pubblicati sono visibili in lettura a chiunque abbia `wiki.read`. Memorie personali no.

## Aiuto e supporto

- `?` o Command Palette → "Aiuto" mostra tutte le scorciatoie.
- Bug / suggerimenti → contatta l'admin del tuo pack.
- Per richieste GDPR (export, erasure) → contatta DPO della tua organizzazione.
