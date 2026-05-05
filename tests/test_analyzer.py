"""Tests for the requirement quality analyzer."""

from __future__ import annotations

from pathlib import Path

from harness.analyzer import analyze, load_requirement
from harness.models import QualityVerdict, Requirement


def test_atomic_requirement_passes(atomic_requirement: Requirement) -> None:
    assessment = analyze(atomic_requirement)
    assert assessment.verdict == QualityVerdict.ATOMIC
    assert assessment.is_atomic is True
    assert assessment.is_testable is True
    assert assessment.is_unambiguous is True


def test_compound_requirement_detected(compound_requirement: Requirement) -> None:
    assessment = analyze(compound_requirement)
    assert assessment.verdict == QualityVerdict.COMPOUND
    assert assessment.is_atomic is False
    assert len(assessment.sub_requirements) > 1


def test_load_yaml_requirement(repo_root: Path) -> None:
    req = load_requirement(repo_root / "requirements" / "sources" / "REQ-SYS-AEB-001.yaml")
    assert req.id == "REQ-SYS-AEB-001"
    assert req.asil == "C"
    assert len(req.acceptance_criteria) >= 1


def test_untestable_language() -> None:
    req = Requirement(
        id="REQ-TEST-BAD",
        title="Bad requirement",
        description="The system shall provide a user-friendly and intuitive interface.",
        acceptance_criteria=[],
    )
    assessment = analyze(req)
    assert assessment.is_testable is False


def test_ambiguous_language() -> None:
    req = Requirement(
        id="REQ-TEST-AMBIG",
        title="Ambiguous requirement",
        description="The system shall respond in a reasonable time, typically under 500 ms.",
        acceptance_criteria=[
            {  # type: ignore[list-item]
                "id": "AC-1",
                "text": "Response time < 500ms",
                "metric": "response_time",
                "threshold": 500,
                "type": "analog",
            }
        ],
    )
    from harness.models import AcceptanceCriterion

    req.acceptance_criteria = [
        AcceptanceCriterion(
            id="AC-1", text="Response time", metric="t", threshold=500, type="analog"
        )
    ]
    assessment = analyze(req)
    assert assessment.is_unambiguous is False
