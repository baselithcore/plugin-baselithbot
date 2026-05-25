# Auth Plugin - Sistema di Autenticazione Enterprise-Grade

**Last Updated**: 2026-01-14 | **Version**: 2.0.0 | **Status**: ✅ Production Ready

Plugin per l'autenticazione e autorizzazione del Baselith-Core. Fornisce autenticazione moderna con password, MFA, WebAuthn/Passkey, risk assessment e controllo accessi role-based (RBAC).

## 🚀 Caratteristiche Principali

### Autenticazione

- 🔐 **Password Security**: Argon2id hashing, breach detection (HIBP), password policy enforcement
- 📱 **MFA/2FA**: TOTP authenticator apps + backup codes
- 🔑 **Passwordless**: WebAuthn/Passkey (Touch ID, Face ID, YubiKey)
- 🎯 **Risk-Based Auth**: Adaptive authentication based on context

### Sicurezza

- 🛡️ **Session Protection**: Session fixation prevention, automatic token rotation
- 🚫 **CSRF Protection**: Double Submit Cookie pattern with explicit validation
- ⚡ **Rate Limiting**: Distributed with exponential backoff (Redis-backed)
- 📊 **Audit Logging**: Comprehensive security event tracking

### Gestione

- 🎭 **RBAC**: 4 ruoli (`admin`, `user`, `guest`, `anonymous`) con permessi granulari
- 🍪 **Session Management**: Refresh tokens in HttpOnly cookies, RFC 7009 revocation
- 🆘 **Account Recovery**: Secure password reset and account unlock
- 🛠️ **Admin Panel**: Web UI per gestione utenti e audit logs

---

## Quick Start

### 1. Crea il primo admin

```bash
python scripts/create_user.py --email admin@tuodominio.com --password TuaPasswordSicura123! --role admin
```

### 2. Abilita autenticazione in `.env.prod`

```bash
AUTH_REQUIRED=true
SECRET_KEY=<genera-una-chiave-sicura-32-caratteri>
```

### 3. Riavvia

```bash
docker-compose -f docker-compose.prod.yml up -d
```

---

## 📚 Documentazione

### Get Started (5 minutes)

- **[Quick Start Guide](QUICK_START.md)** ⭐ - Setup rapido e primi test
- **[Security Enhancements 2026](SECURITY_ENHANCEMENTS_2026.md)** - Guida completa alle nuove funzionalità
- **[Implementation Summary](IMPLEMENTATION_SUMMARY.md)** - Riepilogo tecnico dell'implementazione

### Core Documentation

1. **[Architettura](docs/architecture.md)** - Design del sistema, flussi e database schema
2. **[Guida all'Uso](docs/usage.md)** - Comandi CLI e riferimento API
3. **[Sicurezza](docs/security.md)** - Contromisure di sicurezza implementate
4. **[Maintenance](docs/maintenance.md)** - Disaster recovery e operazioni
5. **[MFA Setup](docs/mfa_setup.md)** - Configurazione autenticazione a due fattori

### Integration Guides

- **[Plugin Integration](docs/integration.md)** - Guida per sviluppatori
- **[Custom Plugin Protection](docs/custom_plugin_integration.md)** - Tutorial protezione plugin

### Audit & Security

- **[Security Audit](SECURITY_AUDIT.md)** - Audit report 2026-01-11
- **[Username Feature](USERNAME_FEATURE.md)** - Login con username (alternativa email)

---

## ⚙️ Configurazione

### Core Settings

| Variabile | Descrizione | Default |
|-----------|-------------|---------|
| `AUTH_REQUIRED` | Abilita controllo accessi globale | `false` |
| `SECRET_KEY` | Chiave segreta per JWT (32+ chars) | `None` |
| `AUTH_SESSION_LIFETIME` | Durata access token (secondi) | `900` (15 min) |
| `AUTH_REFRESH_LIFETIME` | Durata refresh token (secondi) | `604800` (7 giorni) |

### Password Policy

| Variabile | Descrizione | Default |
|-----------|-------------|---------|
| `AUTH_PASSWORD_MIN_LENGTH` | Lunghezza minima password | `12` |
| `AUTH_CHECK_PWNED_PASSWORDS` | Check breach database (HIBP) | `true` |
| `AUTH_MAX_LOGIN_ATTEMPTS` | Tentativi prima lockout | `5` |
| `AUTH_LOCKOUT_DURATION_MINUTES` | Durata lockout (minuti) | `15` |

### MFA Settings

| Variabile | Descrizione | Default |
|-----------|-------------|---------|
| `AUTH_MFA_ENABLED` | Abilita supporto MFA | `true` |
| `AUTH_MFA_ISSUER` | Nome visualizzato in authenticator app | `"Baselith-Core"` |

### Account Recovery (Optional)

| Variabile | Descrizione | Default |
|-----------|-------------|---------|
| `AUTH_ACCOUNT_RECOVERY_ENABLED` | Abilita password reset/unlock (richiede SMTP) | `false` |

**Note**: Disabilitato di default. Abilita solo dopo aver configurato SMTP per invio email.

### WebAuthn / Passkey (Optional)

| Variabile | Descrizione | Default |
|-----------|-------------|---------|
| `AUTH_WEBAUTHN_ENABLED` | Abilita WebAuthn/Passkey | `false` |
| `AUTH_WEBAUTHN_RP_ID` | Relying Party ID (dominio) | `"localhost"` |
| `AUTH_WEBAUTHN_RP_NAME` | Nome app per authenticator | `"Baselith-Core"` |
| `AUTH_WEBAUTHN_ORIGIN` | Origin URL completo | `"http://localhost:8000"` |

### Cookie Settings

| Variabile | Descrizione | Default |
|-----------|-------------|---------|
| `AUTH_COOKIE_SECURE` | Flag Secure (richiede HTTPS) | `true` |
| `AUTH_COOKIE_SAMESITE` | Policy SameSite | `"Lax"` |
| `AUTH_COOKIE_HTTPONLY` | Flag HttpOnly | `true` |
| `AUTH_COOKIE_NAME` | Nome cookie refresh token | `"refresh_token"` |

---

## 🔌 API Endpoints

### Authentication

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/auth/login` | POST | Login con email/username + password |
| `/api/auth/logout` | POST | Logout e revoca refresh token |
| `/api/auth/refresh` | POST | Refresh access token |
| `/api/auth/revoke` | POST | Revoca token manualmente (RFC 7009) |
| `/api/auth/me` | GET | Info utente corrente |

### CSRF Protection

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/auth/csrf-token` | GET | Ottieni CSRF token per richieste POST/PUT/DELETE |

### MFA

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/auth/mfa/setup` | POST | Inizia setup MFA (genera QR code) |
| `/api/auth/mfa/enable` | POST | Abilita MFA dopo verifica codice |
| `/api/auth/mfa/disable` | POST | Disabilita MFA (admin only) |
| `/api/auth/mfa/verify` | POST | Verifica codice TOTP/backup |

### WebAuthn / Passkey (se abilitato)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/auth/webauthn/register/start` | POST | Inizia registrazione credenziale |
| `/api/auth/webauthn/register/finish` | POST | Completa registrazione |
| `/api/auth/webauthn/authenticate/start` | POST | Inizia autenticazione passwordless |
| `/api/auth/webauthn/authenticate/finish` | POST | Completa autenticazione |

### Admin Panel

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/auth/admin/users` | GET | Lista utenti |
| `/api/auth/admin/users` | POST | Crea utente |
| `/api/auth/admin/users/{id}` | GET | Dettagli utente |
| `/api/auth/admin/users/{id}` | PUT | Modifica utente |
| `/api/auth/admin/users/{id}` | DELETE | Elimina utente |
| `/api/auth/admin/audit` | GET | Log audit azioni admin |

Documentazione completa API: `http://localhost:8000/docs` (Swagger UI)

---

## 🔒 Security Features

### Breach Detection

- **HIBP Integration**: Check automatico password contro 15+ miliardi di credenziali compromesse
- **k-anonymity**: Solo primi 5 caratteri dell'hash SHA-1 inviati all'API
- **Performance**: ~200ms overhead, solo su registrazione/password change

### Session Security

- **Session Fixation Prevention**: Revoca automatica token precedenti al login
- **Token Rotation**: Refresh token ruotati automaticamente
- **Secure Cookies**: HttpOnly, Secure, SameSite=Lax

### Explicit CSRF Protection

- **Double Submit Cookie**: Token in cookie + header validation
- **Constant-time Comparison**: Prevenzione timing attacks
- **Frontend Integration**: Endpoint `/api/auth/csrf-token`

### Rate Limiting

- **Distributed**: Redis-backed per multi-instance
- **Exponential Backoff**: 5min → 10min → 20min → 40min → 60min
- **Sliding Window**: Algoritmo più accurato del fixed window
- **Per-IP & Per-User**: Tracking granulare

### Risk Assessment

- **Context Analysis**: IP, device, User-Agent, login time
- **Behavioral Baseline**: Ultimo 20 autenticazioni per utente
- **Adaptive MFA**: Richiede MFA per login sospetti
- **Audit Logging**: Log dettagliati per investigazioni

---

## 📦 Dependencies

```txt
# Core authentication
argon2-cffi>=23.1.0          # Password hashing
PyJWT==2.8.0                  # JWT tokens
pyotp>=2.9.0                  # MFA/TOTP
qrcode[pil]>=7.4.0           # QR code generation

# Security enhancements (v2.0)
webauthn>=2.2.0              # Passwordless auth
user-agents>=2.2.0           # Device fingerprinting
httpx==0.27.0                # HIBP API client

# Infrastructure
redis==5.0.7                 # Rate limiting, caching
psycopg[binary,pool]==3.2.1  # PostgreSQL
fastapi==0.115.0             # Web framework
fastapi-limiter>=0.1.6       # Rate limiting
```

---

## 🎯 Compliance & Standards

| Standard | Status | Notes |
|----------|--------|-------|
| **NIST SP 800-63B** | ✅ Full | Digital Identity Guidelines |
| **OWASP Top 10 2021** | ✅ 10/10 | All categories addressed |
| **RFC 7009** | ✅ Yes | Token Revocation |
| **W3C WebAuthn L3** | ✅ Yes | Passwordless auth |
| **FIDO2 CTAP2** | ✅ Yes | Hardware authenticators |
| **GDPR** | ⚠️ Partial | Data export/deletion pending |
| **SOC 2 Type II** | ⚠️ Partial | Formal audit needed |

---

## 🧪 Testing

```bash
# Run all auth tests
pytest tests/unit/plugins_tests/auth/ -v

# Run with coverage
pytest tests/unit/plugins_tests/auth/ --cov=plugins.auth --cov-report=html

# Test specific module
pytest tests/unit/plugins_tests/auth/test_security.py -v

# Integration tests
pytest tests/integration/ -k auth -v
```

---

## 🚀 Production Deployment

### Pre-Flight Checklist

- [ ] `SECRET_KEY` configurato (32+ caratteri random)
- [ ] `AUTH_COOKIE_SECURE=true` (richiede HTTPS)
- [ ] Redis configurato per rate limiting
- [ ] Database migrato (`schema.sql` applicato)
- [ ] Primo admin creato (`scripts/create_user.py`)
- [ ] CSRF protection integrato nel frontend
- [ ] Email SMTP configurato (per recovery)
- [ ] Monitoring configurato (Prometheus metrics)
- [ ] Backup automatico abilitato

### Performance Tuning

```bash
# .env production
AUTH_SESSION_LIFETIME=900           # 15 min (default ok)
AUTH_REFRESH_LIFETIME=604800        # 7 giorni (default ok)
AUTH_CHECK_PWNED_PASSWORDS=true     # Raccomandato
AUTH_MAX_LOGIN_ATTEMPTS=5           # Adjust per use case
```

### Redis Setup (Required for Production)

```bash
# docker-compose.yml
redis:
  image: redis:7-alpine
  ports:
    - "6379:6379"
  volumes:
    - redis_data:/data
  command: redis-server --appendonly yes
```

---

## 🆘 Troubleshooting

### Common Issues

**"HIBP API timeout"**

- Network issues o HIBP down
- Sistema fa fail-open (permette registrazione)
- Disabilita con `AUTH_CHECK_PWNED_PASSWORDS=false`

**"Redis not available"**

- Rate limiting usa fallback in-memory
- Non distribuito su multi-instance
- Fix: Configura Redis in `.env`

**"CSRF token missing"**

- Frontend non invia header `X-CSRF-Token`
- Fix: Chiama `/api/auth/csrf-token` prima

**"WebAuthn not working"**

- Richiede HTTPS (o localhost per test)
- Browser deve supportare WebAuthn
- Verifica `AUTH_WEBAUTHN_ORIGIN` corretto

### Debug Mode

```bash
# Abilita logging dettagliato
LOG_LEVEL=DEBUG python -m core.cli run

# Tail dei log
tail -f logs/app.log | grep -E "(AUTH|SECURITY)"
```

---

## 📝 Changelog

### v2.0.0 (2026-01-14) - Security Enhancements

**Added**:

- ✨ Compromised password detection (HIBP API)
- ✨ WebAuthn/Passkey support (Touch ID, Face ID, YubiKey)
- ✨ Risk-based authentication with context analysis
- ✨ Explicit CSRF protection (Double Submit Cookie)
- ✨ Token revocation endpoint (RFC 7009)
- ✨ Enhanced rate limiting with exponential backoff
- ✨ Account recovery mechanisms

**Security**:

- 🛡️ Session fixation prevention
- 🛡️ Automatic token rotation on login
- 🛡️ Distributed rate limiting (Redis)
- 🛡️ Audit logging enhancements

**Documentation**:

- 📚 Complete security guide
- 📚 Quick start guide (5 minutes)
- 📚 Implementation summary
- 📚 API reference updates

### v1.x - Previous Versions

See [SECURITY_AUDIT.md](SECURITY_AUDIT.md) for details.

---

## 🤝 Contributing

Per contribuire al plugin auth:

1. Leggi [CLAUDE.md](../../CLAUDE.md) per architettura del sistema
2. Segui coding standards (type hints, docstrings)
3. Aggiungi test per nuove feature
4. Aggiorna documentazione
5. Run `pytest` e `python -m core.cli lint`

---

## 📄 License

Parte del Baselith-Core framework.

---

## 🔗 Resources

- **NIST SP 800-63B**: <https://pages.nist.gov/800-63-3/sp800-63b.html>
- **OWASP Auth Cheatsheet**: <https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html>
- **HaveIBeenPwned API**: <https://haveibeenpwned.com/API/v3>
- **W3C WebAuthn**: <https://www.w3.org/TR/webauthn-3/>
- **RFC 7009**: <https://datatracker.ietf.org/doc/html/rfc7009>

---

**Last Updated**: 2026-01-14 | **Version**: 2.0.0
