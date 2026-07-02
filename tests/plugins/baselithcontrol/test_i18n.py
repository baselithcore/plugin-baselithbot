"""Backend i18n: locale negotiation + catalog lookup (en default, it complete)."""

from __future__ import annotations

import json
from pathlib import Path

from plugins.baselithcontrol.i18n import negotiate_locale, translate

_LOCALES = Path(__file__).resolve().parents[3] / "plugins/baselithcontrol/locales"


def test_negotiate_locale_prefers_quality_and_supported() -> None:
    assert negotiate_locale(None) == "en"
    assert negotiate_locale("it") == "it"
    assert negotiate_locale("it-IT,it;q=0.9,en;q=0.5") == "it"
    assert negotiate_locale("fr-FR,fr;q=0.9") == "en"  # unsupported → default
    assert negotiate_locale("fr;q=0.9,it;q=0.4") == "it"  # best *supported* wins
    assert negotiate_locale("garbage;;q=x") == "en"


def test_translate_interpolates_and_falls_back() -> None:
    assert (
        translate("control.action.not_found", "en", plugin="x")
        == "Plugin 'x' is not registered."
    )
    assert "non è registrato" in translate("control.action.not_found", "it", plugin="x")
    # Unknown key degrades to the key id, never raises.
    assert translate("no.such.key", "it") == "no.such.key"
    # Unsupported locale falls back to English.
    assert "registered" in translate("control.action.not_found", "de", plugin="x")


def test_catalogs_have_full_key_parity() -> None:
    en = json.loads((_LOCALES / "en.json").read_text(encoding="utf-8"))
    it = json.loads((_LOCALES / "it.json").read_text(encoding="utf-8"))
    assert set(en) == set(it)
    assert all(v.strip() for v in en.values()) and all(v.strip() for v in it.values())
