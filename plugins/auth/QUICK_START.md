# Auth Plugin Security Enhancements - Quick Start

**5-Minute Setup Guide** per testare le nuove funzionalità di sicurezza.

---

## Step 1: Install Dependencies (30 seconds)

```bash
pip install -r requirements.txt
```

Nuove dipendenze installate:

- `webauthn>=2.2.0`
- `user-agents>=2.2.0`

---

## Step 2: Update Environment (1 minute)

Aggiungi al tuo `.env` (o crea se non esiste):

```bash
# === Enable Pwned Password Check ===
AUTH_CHECK_PWNED_PASSWORDS=true

# === WebAuthn (optional, per test successivi) ===
AUTH_WEBAUTHN_ENABLED=false  # Lascia false per ora
AUTH_WEBAUTHN_RP_ID=localhost
AUTH_WEBAUTHN_RP_NAME="Baselith-Core"
AUTH_WEBAUTHN_ORIGIN=http://localhost:8000
```

---

## Step 3: Update Database (30 seconds)

Crea la tabella per WebAuthn credentials:

```bash
# Option A: Reset completo (development)
python scripts/reset_all.py

# Option B: Apply solo nuovo schema (production)
psql -d your_database -f plugins/auth/schema.sql
```

---

## Step 4: Start Server (10 seconds)

```bash
python -m core.cli run --reload
```

---

## Step 5: Quick Tests (3 minutes)

### Test 1: Pwned Password Detection ⭐

```bash
# Questo dovrebbe FALLIRE (password nota)
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "password123"
  }'

# Expected response:
# {
#   "detail": "Password has been exposed in 9545824 data breaches. Please choose a different password."
# }
```

```bash
# Questo dovrebbe FUNZIONARE (password sicura)
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test2@example.com",
    "password": "Xk9#mP2$vL8@qN4!"
  }'

# Expected: 200 OK
```

---

### Test 2: CSRF Protection 🔐

```bash
# Get CSRF token
curl http://localhost:8000/api/auth/csrf-token

# Expected response:
# {
#   "csrf_token": "very_long_random_string"
# }
```

**Token viene anche settato come cookie**. Verifica:

```bash
curl -i http://localhost:8000/api/auth/csrf-token | grep -i set-cookie
```

---

### Test 3: Rate Limiting ⚡

```bash
# Prova 7 login falliti rapidamente
for i in {1..7}; do
  echo "=== Attempt $i ==="
  curl -i -X POST http://localhost:8000/api/auth/login \
    -H "Content-Type: application/json" \
    -d '{"identifier":"nonexistent@example.com","password":"wrong"}'
  sleep 2
done

# Dopo 5 tentativi dovresti ricevere:
# HTTP/1.1 429 Too Many Requests
# Retry-After: 300
```

---

### Test 4: Token Revocation 📜

Prima crea un utente e fai login:

```bash
# 1. Login
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"identifier":"your_user@example.com","password":"your_password"}' \
  -c cookies.txt

# 2. Revoca il token
curl -X POST http://localhost:8000/api/auth/revoke \
  -b cookies.txt \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"

# Expected: {"message":"Token revoked successfully"}

# 3. Prova a usare il token revocato
curl -X POST http://localhost:8000/api/auth/refresh -b cookies.txt

# Expected: 401 Unauthorized
```

---

### Test 5: Session Fixation Protection 🛡️

```bash
# 1. First login
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"identifier":"user@example.com","password":"password"}' \
  -c cookies1.txt -v

# 2. Second login (same user)
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"identifier":"user@example.com","password":"password"}' \
  -c cookies2.txt -v

# 3. Il primo cookie NON dovrebbe più funzionare
curl http://localhost:8000/api/auth/me -b cookies1.txt

# Expected: 401 Unauthorized (token revocato)
```

---

## Verify Logs

Controlla i log per vedere le feature in azione:

```bash
tail -f logs/app.log | grep -i "risk\|pwned\|revoked\|csrf"
```

Dovresti vedere log come:

```text
INFO - Password found in 9545824 breaches
INFO - Revoked 2 previous tokens for user abc-123
INFO - Risk assessment for user xyz: score=0.35, action=allow
INFO - Token revoked for user abc-123 by abc-123
```

---

## What's Working Now

✅ **Pwned Password Detection**

- Tutti i nuovi utenti e password changes vengono controllati
- ~200ms overhead per chiamata API HIBP

✅ **Session Fixation Protection**

- Al login, tutti i token precedenti vengono revocati automaticamente
- Previene attacchi di session hijacking

✅ **CSRF Protection**

- Endpoint `/api/auth/csrf-token` disponibile
- Frontend deve includere `X-CSRF-Token` header

✅ **Token Revocation**

- Endpoint `/api/auth/revoke` RFC 7009 compliant
- Utenti possono terminare sessioni manualmente

✅ **Enhanced Rate Limiting**

- Exponential backoff per repeat offenders
- Distributed via Redis (se disponibile)

✅ **Risk Assessment**

- Analisi contestuale passiva
- Log warnings per login sospetti

✅ **Account Recovery**

- Infrastructure pronta (email integration pending)

✅ **WebAuthn Support**

- Backend completo
- Frontend UI da implementare

---

## Next Steps

### For Development

1. **Test tutti gli endpoint nuovi**:

   ```bash
   pytest tests/unit/plugins_tests/auth/ -v
   ```

2. **Integra CSRF nel frontend**:

   ```javascript
   // Get token on app init
   const { csrf_token } = await fetch('/api/auth/csrf-token').then(r => r.json());

   // Use in requests
   fetch('/api/endpoint', {
     method: 'POST',
     headers: { 'X-CSRF-Token': csrf_token }
   });
   ```

3. **Monitor logs**:

   ```bash
   tail -f logs/app.log | grep -E "(SECURITY|risk|pwned|CSRF)"
   ```

### For Production

1. **Configure Redis** (rate limiting, challenges):

   ```bash
   # .env
   REDIS_URL=redis://your-redis-host:6379/1
   ```

2. **Enable WebAuthn** (quando pronto):

   ```bash
   AUTH_WEBAUTHN_ENABLED=true
   AUTH_WEBAUTHN_RP_ID=your-domain.com
   AUTH_WEBAUTHN_ORIGIN=https://your-domain.com
   ```

3. **Setup Email** (account recovery):
   - Configure SMTP in config
   - Implement email templates
   - Test password reset flow

---

## Troubleshooting

### "HIBP API timeout"

**Cause**: Network issues or HIBP downtime
**Fix**: Fail-open design allows registration (logged as warning)
**Config**: Disable with `AUTH_CHECK_PWNED_PASSWORDS=false`

### "Redis not available - using in-memory rate limiting"

**Cause**: Redis not configured
**Impact**: Rate limiting works but not distributed across instances
**Fix**: Configure Redis connection in `.env`

### "webauthn not installed"

**Cause**: Missing dependency
**Fix**: `pip install webauthn>=2.2.0`

### "CSRF token missing"

**Cause**: Frontend not sending X-CSRF-Token header
**Fix**: Call `/api/auth/csrf-token` first, include in requests

---

## Performance Checklist

Monitor these metrics:

```python
# Add to your monitoring
metrics = {
    "login_latency_p95": "< 500ms",  # With HIBP check
    "refresh_latency_p95": "< 100ms",
    "rate_limit_check": "< 10ms",
    "risk_assessment": "< 5ms",
}
```

---

## Security Checklist

Before going to production:

- [ ] Redis configured for rate limiting
- [ ] CSRF token enforced on all POST/PUT/DELETE
- [ ] WebAuthn tested on iOS/Android/Desktop
- [ ] Email sending configured (SMTP/SendGrid)
- [ ] Audit logs reviewed
- [ ] Performance tested under load
- [ ] Backup strategy for auth DB tables

---

## Resources

- **Full Documentation**: [SECURITY_ENHANCEMENTS_2026.md](SECURITY_ENHANCEMENTS_2026.md)
- **Implementation Details**: [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md)
- **Code**: `plugins/auth/*.py`
- **Tests**: `tests/unit/plugins_tests/auth/`

---

**Ready to test!** 🚀

Se hai problemi, controlla i log e la documentazione completa.

Per SSO (OAuth/SAML), programma una sessione dedicata quando sei pronto.
