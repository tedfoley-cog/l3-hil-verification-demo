"""Tests for the Gherkin decomposer."""

from __future__ import annotations

from harness.analyzer import analyze
from harness.decomposer import decompose, format_scenarios
from harness.models import QualityVerdict, Requirement


def test_atomic_produces_single_scenario(atomic_requirement: Requirement) -> None:
    assessment = analyze(atomic_requirement)
    scenarios = decompose(atomic_requirement, assessment)
    assert len(scenarios) == 1
    assert scenarios[0].parent_requirement_id == atomic_requirement.id


def test_compound_produces_multiple_scenarios(compound_requirement: Requirement) -> None:
    assessment = analyze(compound_requirement)
    assert assessment.verdict == QualityVerdict.COMPOUND
    scenarios = decompose(compound_requirement, assessment)
    assert len(scenarios) > 1
    for s in scenarios:
        assert s.parent_requirement_id == compound_requirement.id


def test_scenarios_have_given_when_then(compound_requirement: Requirement) -> None:
    assessment = analyze(compound_requirement)
    scenarios = decompose(compound_requirement, assessment)
    for s in scenarios:
        assert len(s.given_steps) > 0
        assert len(s.when_steps) > 0
        assert len(s.then_steps) > 0


def test_format_scenarios_produces_gherkin(compound_requirement: Requirement) -> None:
    assessment = analyze(compound_requirement)
    scenarios = decompose(compound_requirement, assessment)
    gherkin_text = format_scenarios(scenarios)
    assert "Feature:" in gherkin_text
    assert "Scenario:" in gherkin_text
    assert "Given" in gherkin_text
    assert "When" in gherkin_text
    assert "Then" in gherkin_text


def test_traceability_tags_present(compound_requirement: Requirement) -> None:
    assessment = analyze(compound_requirement)
    scenarios = decompose(compound_requirement, assessment)
    for s in scenarios:
        assert compound_requirement.id in s.tags
        assert f"ASIL-{compound_requirement.asil}" in s.tags
