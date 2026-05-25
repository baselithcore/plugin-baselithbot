# Auth Plugin - Guida all'Uso (CLI & API)

Questo documento fornisce istruzioni dettagliate per gestire gli utenti tramite la CLI e interagire con le API di autenticazione.

## Gestione Utenti (CLI)

Il framework utilizza un approccio "Command Line First" per la gestione degli utenti amministrativi. Lo script si trova in `scripts/create_user.py`.

### Operazioni Comuni

| Comando | Descrizione |
|---------|-------------|
| `--email` | Crea un nuovo utente (se non usato con altri flag action) |
| `--list` | Elenca tutti gli utenti registrati |
| `--disable/--enable` | Attiva o disattiva un account |
| `--reset-mfa` | Rimuove il segreto MFA da un utente |
| `--change-password` | Aggiorna la password di un utente |
| `--delete` | Rimuove definitivamente un utente |

### Esempi Pratici

**Creazione Admin:**

```bash
python scripts/create_user.py --email admin@system.local --password "SecurePass123!" --role admin
```

**Creazione Guest con restrizioni tab:**

```bash
python scripts/create_user.py --email viewer@client.it --role guest --allowed-tabs honeypot,analytics
```

---

## API Reference

Il plugin espone i suoi endpoint sotto il prefisso `/api/auth`. Ogni risposta di errore segue lo standard RFC 7807 (Problem Details).

### Autenticazione

#### `POST /login`

Inizia la sessione. Se l'MFA è attivo, restituisce un `temp_token`.

- **Payload**: `{"email": "...", "password": "..."}`
- **Successo (No MFA)**: `200 OK` con Access Token.
- **Successo (MFA)**: `200 OK` con `mfa_required: true`.

#### `POST /mfa/verify`

Completa il login MFA.

- **Payload**: `{"temp_token": "...", "code": "123456"}`

#### `POST /refresh`

Rinnova l'access token usando il refresh token salvato nel cookie HttpOnly.

- **Input**: Cookie `refresh_token`.
- **Note**: Esegue la rotazione del token (invalida il precedente).

#### `POST /logout`

Invalida la sessione corrente e rimuove il cookie.

### Profilo Utente

#### `GET /me`

Restituisce le informazioni sull'utente corrente.

- **Ritorna**: ID, email, ruoli, stato MFA, tab autorizzati.

### Configurazione MFA

#### `POST /mfa/setup`

Avvia il setup MFA (solo utenti autenticati). Genera un nuovo segreto e codici di backup.

- **Ritorna**: Secret, provisioning URI, QR code (base64) e backup codes.

#### `POST /mfa/enable`

Conferma e abilita l'MFA dopo aver verificato un codice di setup.

#### `POST /mfa/disable`

Disabilita l'MFA. Richiede ruolo `admin` se si agisce su un altro utente.

### Admin API (Richieste `role: admin`)

#### `GET /admin/users`

Elenco utenti paginato con filtri.

- **Query Params**: `page`, `limit`, `include_inactive`, `search`.

#### `POST /admin/users`

Crea un nuovo utente.

- **Payload**: `{"email": "...", "roles": ["user"], "allowed_tabs": [...]}`
- **Ritorna**: Password temporanea (se non fornita).

#### `GET /admin/audit-log`

Consulta il registro di audit immodificabile.

- **Query Params**: `action`, `actor_id`, `target_id`, `page`, `limit`.

---

## Troubleshooting

### Lockout Account

Se un utente supera il numero massimo di tentativi (`AUTH_MAX_LOGIN_ATTEMPTS`), l'account viene bloccato per `AUTH_LOCKOUT_DURATION_MINUTES`.

- **Soluzione**: Attendere il timeout o resettare la password via CLI per sbloccare immediatamente.

### Refresh Token non inviato

Assicurarsi che il frontend sia configurato per inviare le credenziali (cookies) nelle richieste cross-origin (`withCredentials: true` o `credentials: 'include'`).
