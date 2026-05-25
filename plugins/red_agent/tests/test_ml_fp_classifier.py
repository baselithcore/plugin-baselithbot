"""M1 — FP classifier service tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from plugins.red_agent.ml.models.features import (
    FEATURE_NAMES,
    extract_features,
    feature_dim,
)
from plugins.red_agent.ml.models.fp_classifier import (
    FPClassifierService,
    train_classifier,
)
from plugins.red_agent.models import Finding, Severity


def _finding(**kw: object) -> Finding:
    base: dict[str, object] = {
        "scanner": "nuclei",
        "title": "t",
        "description": "d",
        "severity": Severity.MEDIUM,
        "target": "example.com",
    }
    base.update(kw)
    return Finding(**base)  # type: ignore[arg-type]


def test_feature_extractor_dimension_matches_names() -> None:
    f = _finding()
    vec = extract_features(f)
    assert len(vec) == feature_dim()
    assert len(vec) == len(FEATURE_NAMES)


def test_feature_extractor_is_deterministic() -> None:
    f = _finding(endpoint="https://example.com/login", port=8080, cvss_score=7.5)
    assert extract_features(f) == extract_features(f)


def test_classifier_disabled_returns_findings_unchanged() -> None:
    svc = FPClassifierService(model_path=None, drop_threshold=0.8, enabled=True)
    f = _finding()
    out = svc.annotate_and_filter([f])
    assert out == [f]
    assert svc.score(f) is None


def test_classifier_disabled_when_path_missing(tmp_path: Path) -> None:
    svc = FPClassifierService(
        model_path=tmp_path / "nope.joblib", drop_threshold=0.8, enabled=True
    )
    assert svc.enabled is False


def test_train_then_load_then_predict_roundtrip(tmp_path: Path) -> None:
    pytest.importorskip("sklearn")
    pytest.importorskip("joblib")

    # Fabricate a tiny labeled corpus where INFO-severity findings without
    # CVSS are FPs and HIGH-severity findings with CVSS are real. The
    # classifier should learn a clean split on these features.
    samples: list[tuple[Finding, bool]] = []
    for _ in range(15):
        samples.append((_finding(severity=Severity.INFO), True))
        samples.append(
            (_finding(severity=Severity.HIGH, cvss_score=8.5, cwe="CWE-89"), False)
        )

    out_path = tmp_path / "fp.joblib"
    summary = train_classifier(samples=samples, output_path=out_path)
    assert summary["samples"] == len(samples)
    assert out_path.exists()

    svc = FPClassifierService(model_path=out_path, drop_threshold=0.5, enabled=True)
    assert svc.enabled is True

    fp_score = svc.score(_finding(severity=Severity.INFO))
    tp_score = svc.score(_finding(severity=Severity.HIGH, cvss_score=8.5, cwe="CWE-89"))
    assert fp_score is not None and tp_score is not None
    assert fp_score > tp_score
    assert fp_score >= 0.5  # info-class should be flagged as FP


def test_annotate_and_filter_drops_high_score_findings(tmp_path: Path) -> None:
    pytest.importorskip("sklearn")
    pytest.importorskip("joblib")

    samples: list[tuple[Finding, bool]] = []
    for _ in range(15):
        samples.append((_finding(severity=Severity.INFO), True))
        samples.append(
            (_finding(severity=Severity.HIGH, cvss_score=8.5, cwe="CWE-89"), False)
        )
    out_path = tmp_path / "fp.joblib"
    train_classifier(samples=samples, output_path=out_path)

    svc = FPClassifierService(model_path=out_path, drop_threshold=0.5, enabled=True)
    info_finding = _finding(severity=Severity.INFO)
    high_finding = _finding(severity=Severity.HIGH, cvss_score=8.5, cwe="CWE-89")
    out = svc.annotate_and_filter([info_finding, high_finding])
    # High-severity finding survives and carries an ml_fp_score annotation.
    assert any(f.id == high_finding.id for f in out)
    survivor = next(f for f in out if f.id == high_finding.id)
    assert "ml_fp_score" in survivor.evidence


def test_train_rejects_single_class_dataset(tmp_path: Path) -> None:
    pytest.importorskip("sklearn")
    samples = [(_finding(), True) for _ in range(5)]
    with pytest.raises(ValueError):
        train_classifier(samples=samples, output_path=tmp_path / "x.joblib")


def test_load_rejects_feature_version_mismatch(tmp_path: Path) -> None:
    pytest.importorskip("joblib")
    import joblib  # type: ignore[import-untyped]

    artifact = {"model": object(), "feature_version": -1, "trained_at": "x"}
    out = tmp_path / "stale.joblib"
    joblib.dump(artifact, out)

    svc = FPClassifierService(model_path=out, drop_threshold=0.8, enabled=True)
    assert svc.enabled is False
