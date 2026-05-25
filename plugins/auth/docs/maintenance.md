# Guida a Ripristino e Manutenzione (Disaster Recovery)

Questo documento delinea le procedure operative standard per situazioni di emergenza, manutenzione programmata e ripristino dell'accesso al sistema di autenticazione.

## 🚨 Emergency Recovery

Procedure per ripristinare l'accesso in caso di blocco totale, perdita di credenziali o compromissione.

### 1. Smarrimento Password Admin

Se l'unico amministratore ha perso la password o è bloccato:

1. Accedi al server (console/SSH).
2. Esegui il reset forzato della password:

```bash
    python scripts/create_user.py --change-password admin@tuodominio.com --password "NuovaMasterPassword!"
```

*Nota: Questo comando bypassa il rate limiting e lo stato di lockout.*

### 2. Sblocco Account (Lockout)

Se un account è stato bloccato per troppi tentativi falliti:

**Opzione A: Attendi il timeout**
Il blocco scade automaticamente dopo 15 minuti (`AUTH_LOCKOUT_DURATION_MINUTES`).

**Opzione B: Sblocco Immediato**
Disabilitare e riabilitare l'utente resetta i contatori:

```bash
python scripts/create_user.py --disable admin@tuodominio.com
python scripts/create_user.py --enable admin@tuodominio.com
```

### 3. Perdita Dispositivo MFA (2FA)

Se un utente ha perso il telefono e i codici di backup:

1. Reset dell'MFA da riga di comando:

```bash
python scripts/create_user.py --reset-mfa utente@dominio.com
```

1. Al login successivo, il sistema non chiederà il token OTP.
1. L'utente dovrà visitare `/mfa/setup` (o la pagina di profilo) per riconfigurare un nuovo dispositivo.

---

## 🧹 Manutenzione Programmata

### Rotazione Credenziali

Per forzare la rotazione delle password (es. dopo incidente di sicurezza):

1. Inviare comunicazione agli utenti.
2. Resettare le password notificate o invalidare le sessioni:
    *Non esiste un comando CLI "invalidate all sessions" diretto, ma il riavvio del servizio invalida le sessioni in memoria se non persistite su Redis, oppure si può cambiare la `SECRET_KEY`.*

### Cambio SECRET_KEY (Key Rotation)

Se la `SECRET_KEY` in `.env.prod` viene compromessa o ruotata:

1. Aggiorna `.env.prod` con la nuova chiave.
2. Riavvia i container:

```bash
    docker-compose -f docker-compose.prod.yml restart api
```

1. **Effetto**: Tutti i JWT (Access Token) esistenti diventano immediatamente invalidi. Gli utenti dovranno effettuare nuovamente il login.

### Pulizia Utenti Inattivi

Periodicamente, verifica gli utenti registrati per rimuovere account obsoleti:

1. Lista tutti gli utenti (inclusi disabilitati):

```bash
python scripts/create_user.py --list --all
```

1. Identifica account non necessari.
1. Elimina:

```bash
python scripts/create_user.py --delete vecchio.admin@azienda.com
```

---

## 🛡️ Database & Backup

Le tabelle coinvolte sono `auth_users`, `auth_refresh_tokens`, `auth_mfa_backup_codes`.

### Dump dei soli dati Auth

Per fare un backup specifico delle utenze:

```bash
docker exec -t baselith-core-postgres pg_dump -U postgres -t auth_users -t auth_refresh_tokens > auth_backup_$(date +%F).sql
```

### Ripristino

```bash
cat auth_backup_YYYY-MM-DD.sql | docker exec -i baselith-core-postgres psql -U postgres
```

*Attenzione: Il ripristino sovrascrive gli utenti esistenti se ci sono conflitti sugli ID.*
