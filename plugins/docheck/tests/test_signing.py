"""Ed25519 report signing tests."""

from docheck.services.signing import public_key_hex, sign_report, verify_report


def test_sign_and_verify_roundtrip() -> None:
    payload = {"report_id": "r-1", "score": 78, "findings": []}
    sig = sign_report(payload)
    assert sig.startswith("ed25519:")
    assert verify_report(payload, sig, public_key_hex()) is True


def test_tampered_payload_fails_verify() -> None:
    payload = {"report_id": "r-1", "score": 78}
    sig = sign_report(payload)
    tampered = {"report_id": "r-1", "score": 99}
    assert verify_report(tampered, sig, public_key_hex()) is False


def test_invalid_signature_format_rejected() -> None:
    payload = {"x": 1}
    assert verify_report(payload, "not-ed25519:abc", public_key_hex()) is False
