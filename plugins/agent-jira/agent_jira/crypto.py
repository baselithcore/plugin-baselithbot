"""
Envelope encryption per segreti tenant (Sprint 6).

Pattern: MultiFernet con key rotation supportata nativamente.

- La chiave primaria cifra i nuovi valori.
- Le chiavi precedenti possono ancora decifrare valori legacy.
- Per ruotare: aggiungi la nuova chiave in testa a SECRETS_KEYS, mantieni la
  vecchia in coda; opzionalmente riesegui `rotate_all_tenant_secrets()` per
  ri-cifrare tutti i valori con la nuova chiave (maintenance job).

Formato del ciphertext persistito: stringa Fernet (bytes urlsafe base64).

Configurazione:
- `SECRETS_KEYS` env var = lista di chiavi Fernet separate da virgola, in
  ordine decrescente di anzianità (prima = primaria/nuova).
- Fallback legacy: `SECRETS_KEY` (singola chiave) per setup semplici.

Roadmap KMS:
- Questo layer espone `encrypt()`/`decrypt()`. Una futura implementazione KMS
  (AWS KMS, GCP KMS, Vault) può sostituire `_get_fernet()` con un wrapper che
  chiama il KMS per operazioni envelope, senza impatto sui chiamanti.
"""

from __future__ import annotations

import logging
import os
from functools import lru_cache
from typing import Optional

logger = logging.getLogger(__name__)


class SecretsKeyMissingError(RuntimeError):
    """Sollevata se i segreti sono richiesti ma nessuna chiave è configurata."""


def _load_keys_from_env() -> list[str]:
    """Carica le chiavi Fernet da env in ordine di priorità (nuova → vecchia)."""
    multi = os.getenv("SECRETS_KEYS", "").strip()
    if multi:
        return [k.strip() for k in multi.split(",") if k.strip()]
    single = os.getenv("SECRETS_KEY", "").strip()
    if single:
        return [single]
    return []


@lru_cache(maxsize=1)
def _get_fernet():
    """
    Restituisce un MultiFernet configurato con tutte le chiavi note.
    Raise SecretsKeyMissingError se nessuna chiave è presente.
    """
    try:
        from cryptography.fernet import Fernet, MultiFernet
    except ImportError as exc:  # pragma: no cover - dipende da requirements
        raise SecretsKeyMissingError(
            "Package `cryptography` non installato. Installa con `pip install cryptography`."
        ) from exc

    keys = _load_keys_from_env()
    if not keys:
        raise SecretsKeyMissingError(
            "Nessuna chiave di cifratura configurata. "
            "Imposta SECRETS_KEY (singola) o SECRETS_KEYS (comma-separated, "
            "nuova→vecchia) nell'environment. Genera una chiave con:\n"
            "  python -c 'from cryptography.fernet import Fernet; "
            "print(Fernet.generate_key().decode())'"
        )

    fernets = []
    for k in keys:
        try:
            fernets.append(Fernet(k.encode() if isinstance(k, str) else k))
        except Exception as exc:
            raise SecretsKeyMissingError(
                f"Chiave Fernet non valida: {exc}. "
                "Assicurati che sia base64-urlsafe 32 byte."
            )
    return MultiFernet(fernets)


def encrypt(plaintext: str) -> str:
    """
    Cifra un valore in chiaro e restituisce una stringa persistibile.

    Il ciphertext include prefisso schema `enc:v1:` per poter evolvere il
    formato in futuro senza ambiguità sul parsing dei valori esistenti.
    """
    if not plaintext:
        return ""
    fernet = _get_fernet()
    token = fernet.encrypt(plaintext.encode("utf-8")).decode("ascii")
    return f"enc:v1:{token}"


def decrypt(ciphertext: str) -> str:
    """
    Decifra un valore. Accetta sia il nuovo formato `enc:v1:...` sia token
    Fernet "nudi" (per backward-compat durante la migration 007).

    Se il ciphertext non sembra cifrato (valore legacy in chiaro che stia
    passando durante il rollout), lo restituisce invariato. Questa tolleranza
    va rimossa dopo la migration 007 in un release successivo — vedi
    `REMOVE_LEGACY_PLAINTEXT_AFTER_MIGRATION` nel codice chiamante.
    """
    if not ciphertext:
        return ""

    raw = ciphertext
    if ciphertext.startswith("enc:v1:"):
        raw = ciphertext[len("enc:v1:") :]
    elif not _looks_like_fernet_token(ciphertext):
        # Legacy plaintext. Tolleranza temporanea.
        return ciphertext

    try:
        fernet = _get_fernet()
        return fernet.decrypt(raw.encode("ascii")).decode("utf-8")
    except Exception as exc:
        logger.error("Decrypt failed: %s", exc)
        raise


def is_encrypted(value: Optional[str]) -> bool:
    """True se il valore ha il prefisso schema di cifratura applicativa."""
    if not value:
        return False
    return value.startswith("enc:v1:")


def _looks_like_fernet_token(value: str) -> bool:
    """Euristica: un token Fernet è base64-urlsafe lungo ≥100 char."""
    if len(value) < 100:
        return False
    allowed = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_=")
    return all(c in allowed for c in value)


def reset_cache() -> None:
    """Invalida la cache del MultiFernet. Usare dopo rotazione chiavi a caldo."""
    _get_fernet.cache_clear()
