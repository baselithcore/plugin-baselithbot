# Auth Plugin - Sicurezza e Hardening

Il plugin `auth` integra diverse contromisure per garantire la protezione dei dati e la resilienza del sistema contro attacchi comuni.

## Strategie di Protezione

### 1. Hashing delle Password

Utilizziamo **Argon2id** (via `argon2-cffi`), il vincitore della Password Hashing Competition, configurato con parametri che bilanciano sicurezza e performance:

- Gestione automatica del salt.
- Resistenza agli attacchi via GPU/ASIC grazie alla memoria intensiva.
- Funzione `needs_rehash` integrata per futuri aumenti di complessità.

### 2. Gestione dei Session Token (JWT)

- **Breve durata**: Gli access token scadono dopo 15 minuti (`AUTH_SESSION_LIFETIME`).
- **Nessuna persistenza lato server**: Riduce l'overhead e facilita la scalabilità orizzontale.
- **Autorizzazione RBAC**: I ruoli sono codificati nel claim `roles` del JWT.

### 3. Refresh Token e Sicurezza dei Cookie

Per mantenere l'utente loggato senza esporre JWT a lungo termine:

- **HttpOnly**: Impedisce l'accesso ai token via JavaScript (protezione XSS).
- **Secure**: Inviato solo su connessioni HTTPS (in produzione).
- **SameSite=Lax**: Protezione contro attacchi CSRF.
- **Path=/api**: Il cookie è ristretto agli endpoint API, non accessibile da script frontend.
- **Rotazione (Rotation)**: Ogni utilizzo di un refresh token lo invalida e ne emette uno nuovo.

### 3.1 Auto-Refresh Frontend

Gli API client frontend implementano un meccanismo automatico di refresh:

1. Su risposta **401**, il client tenta di refreshare il token (`POST /api/auth/refresh`)
2. Se il refresh ha successo, la richiesta originale viene ripetuta con il nuovo token
3. Se il refresh fallisce, l'utente viene reindirizzato alla pagina di login

### 4. Protezione contro Brute Force e Enumeration

- **Rate Limiting (Redis)**: Implementato un sistema centralizzato e distribuito tramite `fastapi-limiter` collegato a Redis.
    - **Login**: Limite di 5 richieste al minuto per identificatore.
    - **MFA**: Limite di 10 richieste al minuto per utente.
    - I blocchi persistono anche al riavvio dei servizi grazie alla persistenza di Redis.
- **Account Lockout**: Dopo 5 tentativi consecutivi falliti, l'account viene bloccato per 15 minuti (`locked_until` nel database).
- **Anti-Enumeration**: Il sistema esegue un "dummy password check" se l'utente non viene trovato, garantendo che i tempi di risposta siano i medesimi per utenti esistenti e non.

### 5. Multi-Factor Authentication (MFA)

- Basato su **TOTP** (RFC 6238).
- Segreti salvati crittografati o comunque protetti nel DB.
- **Backup Codes**: In caso di perdita del dispositivo, l'utente può utilizzare 10 codici di emergenza monouso, salvati come hash SHA-256.

## Raccomandazioni per il Deploy

1. **SECRET_KEY**: Assicurarsi che sia una stringa casuale di almeno 32 caratteri, unica per ogni ambiente.
2. **HTTPS**: Fondamentale per proteggere i cookies e prevenire attacchi Man-in-the-middle.
3. **Database Hardening**: Limitare l'accesso al DB PostgreSQL solo al servizio API.
4. **Audit Logs**: Monitorare i log di errore del plugin per identificare pattern di attacco (IP che tentano molti account diversi).
