import pytest


@pytest.fixture(autouse=True)
def _isolate(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("DOCHECK_STORAGE_ROOT", str(tmp_path))
    monkeypatch.setenv("DOCHECK_DB_PATH", str(tmp_path / "docheck.db"))
    monkeypatch.setenv("DOCHECK_AUDIT_SIGNING_KEY_PATH", str(tmp_path / "audit.key"))
