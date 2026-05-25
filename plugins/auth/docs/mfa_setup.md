# Guida Configurazione MFA (Multi-Factor Authentication)

Questa guida spiega come abilitare l'autenticazione a due fattori (MFA/TOTP) per gli utenti del sistema utilizzando lo script CLI dedicato.

## Prerequisiti

* Un utente già esistente nel database (creato via `scripts/create_user.py`).
* Accesso al terminale del server/container.
* Un'app Authenticator sul telefono (Google Authenticator, Authy, Microsoft Authenticator, ecc.).

## Abilitazione MFA via CLI

Abbiamo creato uno script di utility per facilitare questa operazione senza dover manipolare il database manualmente.

### Comando

Esegui lo script `scripts/setup_mfa_cli.py` specificando l'email dell'utente.

Se stai lavorando con Docker Compose, eseguilo nel servizio `api`:

```bash
docker compose exec api python scripts/setup_mfa_cli.py --email admin@tuodominio.com
```

Se sei già dentro il container o stai eseguendo localmente dalla root del progetto:

```bash
python scripts/setup_mfa_cli.py --email admin@tuodominio.com
```

### Output Atteso

Lo script eseguirà le seguenti azioni:

1. Genererà un nuovo **Secret** TOTP sicuro.
2. Aggiornerà il record utente nel database impostando `mfa_enabled = True` e salvando il secret.
3. Genererà 10 **backup codes** di recupero e li salverà in forma hash nel database.
4. Mostrerà a video:
    * La **chiave segreta** (stringa alfanumerica) per l'inserimento manuale.
    * L'**URI** standard `otpauth://`.
    * I **backup codes** da conservare in un password manager o in un luogo sicuro.
    * Un **QR Code** ASCII scansionabile direttamente dal terminale.

### Esempio

```text
Setting up MFA for user: admin@system.local
User updated successfully.

==================================================
MFA SETUP COMPLETE
==================================================
Secret Key (manual entry): SECRET_KEY
OTP URI: otpauth://totp/MultiAgentSystem:admin@system.local?secret=SECRET_KEY
Backup Codes (store them securely, shown only now):
  - ABCD-1234
  - EFGH-5678
==================================================

Scan the QR code below...
[QR CODE ASCII]
```

## Troubleshooting

* **QR Code non leggibile**: Se il font del terminale distorce il QR code, usa la "Secret Key" visualizzata sopra il QR code e inseriscila manualmente nell'app ("Inserisci codice impostazione" o "Enter setup key").
* **1Password / Password Manager**:
    * Crea una nuova voce o modifica quella esistente.
    * Aggiungi un campo "One-Time Password" (o "Codice Monouso").
    * Incolla la **Secret Key** (la stringa alfanumerica) fornita dallo script.
    * 1Password inizierà a generare i codici automaticamente.
* **Utente non trovato**: Assicurati che l'email sia corretta e che l'utente sia stato creato prima con `scripts/create_user.py`.
* **MFA già configurato**: Lo script blocca la rotazione accidentale del secret. Se vuoi rigenerare secret e backup codes, usa `--force`.
