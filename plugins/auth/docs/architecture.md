# Auth Plugin - Architettura

Questo documento descrive il design interno, il modello dei dati e i flussi di autenticazione del plugin `auth`.

## Panoramica del Sistema

Il sistema segue un'architettura a plugin plug-and-play, integrandosi con il core del framework tramite middleware e dependency injection di FastAPI.

```mermaid
graph TD
    User((Utente/Browser)) -->|Request| Middleware[AuthMiddleware]
    Middleware -->|JWT/Cookie| AuthManager[Core AuthManager]
    AuthManager -->|Validate| JWTHandler[JWT Handler]
    Middleware -->|Attach User| RequestState[Request State]
    RequestState --> Router[Auth Router]
    Router --> Persistence[AuthPersistence]
    Persistence --> DB[(PostgreSQL)]
```

## Flussi di Autenticazione

### 1. Login e MFA Flow

Il flusso di login supporta l'autenticazione a due fattori (MFA) opzionale. Se l'MFA è abilitato, viene emesso un token temporaneo invece dei token finali.

```mermaid
sequenceDiagram
    participant U as Utente
    participant R as Auth Router
    participant P as Persistence
    participant S as SecureStore
    
    U->>R: POST /login (email, password)
    R->>P: Verifica credenziali
    P-->>R: User Data
    
    alt MFA Disabilitato
        R->>U: 200 OK (Access Token + Set-Cookie Refresh)
    else MFA Abilitato
        R->>S: Store Temp Token (5 min)
        R->>U: 200 OK (MFARequired, Temp Token)
        U->>R: POST /mfa/verify (Temp Token, Code)
        R->>S: Validate Temp Token
        R->>R: Verifica TOTP/Backup Code
        R->>U: 200 OK (Access Token + Set-Cookie Refresh)
    end
```

### 2. Token Refresh Flow

Utilizziamo la rotazione dei refresh token per massimizzare la sicurezza. Ogni volta che un access token viene rinnovato, viene generato un nuovo refresh token e quello vecchio viene invalidato.

```mermaid
sequenceDiagram
    participant U as Utente
    participant R as Auth Router
    participant P as Persistence
    
    U->>R: POST /refresh (Cookie: refresh_token)
    R->>P: Valida & Revoca vecchio token
    P-->>R: User ID
    R->>P: Genera & Store nuovo token
    R->>U: 200 OK (New Access Token + New Cookie)
```

## Modello dei Dati

### Database Schema (ERAD)

```mermaid
erDiagram
    auth_users ||--o{ auth_refresh_tokens : owns
    auth_users ||--o{ auth_mfa_backup_codes : owns
    
    auth_users {
        uuid id PK
        string email UK
        string password_hash
        string[] roles
        string mfa_secret
        boolean mfa_enabled
        boolean is_active
        string[] allowed_tabs
        timestamp locked_until
        integer failed_attempts
    }
    
    auth_refresh_tokens {
        uuid id PK
        uuid user_id FK
        string token_hash
        timestamp expires_at
        timestamp revoked_at
    }
    
    auth_mfa_backup_codes {
        uuid id PK
        uuid user_id FK
        string code_hash
        timestamp used_at
    }

    auth_audit_log {
        uuid id PK
        string action
        string actor_id
        string target_id
        jsonb details
        string ip_address
        timestamp created_at
    }
```

## Componenti Core

1. **AuthPersistence**: Gestisce tutte le operazioni SQL su PostgreSQL, inclusi utenti, sessioni e audit log.
2. **AuthMiddleware**: Estrattore di identità globale che popola `request.state.user`.
3. **SecureTokenStore**: Gestore in-memoria (con TTL) per i token temporanei della transazione MFA (valutare Redis per multi-istanza).
4. **Redis Rate Limiter**: Sistema di protezione distribuito basato su `fastapi-limiter` per prevenire brute-force.
5. **AdminRouter**: Router dedicato per la gestione utenti e audit, protetto da `require_admin`.
6. **AuditLogger**: Servizio centralizzato per la registrazione immodificabile delle azioni amministrative.
7. **CLI Manager**: Script esterno (`scripts/create_user.py`) per la gestione amministrativa out-of-band e bootstrap.
