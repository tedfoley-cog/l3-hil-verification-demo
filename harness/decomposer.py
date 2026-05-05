"""Compound requirement decomposer — splits into atomic Gherkin scenarios.

Takes a requirement assessed as COMPOUND by the analyzer and produces
multiple atomic GherkinScenario objects, each independently testable,
while preserving traceability to the parent requirement.
"""

from __future__ import annotations

import re

from harness.models import GherkinScenario, QualityAssessment, QualityVerdict, Requirement


def decompose(requirement: Requirement, assessment: QualityAssessment) -> list[GherkinScenario]:
    """Decompose a compound requirement into atomic Gherkin scenarios.

    If the requirement is already atomic, returns a single scenario wrapping it.
    """
    if assessment.verdict == QualityVerdict.ATOMIC:
        return [_wrap_atomic(requirement)]

    clauses = _split_clauses(requirement.description)
    scenarios: list[GherkinScenario] = []

    for i, clause in enumerate(clauses, 1):
        scenario = _clause_to_scenario(requirement, clause, i)
        scenarios.append(scenario)

    return scenarios


def _wrap_atomic(req: Requirement) -> GherkinScenario:
    """Wrap an already-atomic requirement as a single Gherkin scenario."""
    given, when, then = _infer_steps(req.description, req.acceptance_criteria)
    return GherkinScenario(
        feature_name=req.title,
        scenario_name=_slugify(req.title),
        tags=[req.id, f"ASIL-{req.asil}", f"domain-{req.domain}"],
        given_steps=given,
        when_steps=when,
        then_steps=then,
        parent_requirement_id=req.id,
        decomposition_index=0,
    )


def _split_clauses(description: str) -> list[str]:
    """Split compound description into independently testable clauses."""
    split_patterns = [
        r",\s*and\s+the\b",
        r"\band\s+the\s+\w+\s+shall\b",
    ]
    parts = [description]
    for pattern in split_patterns:
        new_parts: list[str] = []
        for part in parts:
            segments = re.split(pattern, part, flags=re.IGNORECASE)
            new_parts.extend(s.strip() for s in segments if s.strip())
        parts = new_parts

    return [p for p in parts if len(p) > 15]


def _clause_to_scenario(req: Requirement, clause: str, index: int) -> GherkinScenario:
    """Convert a single clause into a Gherkin scenario."""
    given, when, then = _infer_steps_from_clause(clause)

    short_title = _extract_short_title(clause)
    scenario_name = f"{req.title} — {short_title}" if short_title else f"{req.title} (part {index})"

    return GherkinScenario(
        feature_name=req.title,
        scenario_name=scenario_name,
        tags=[
            req.id,
            f"ASIL-{req.asil}",
            f"domain-{req.domain}",
            f"decomposed-{index}",
        ],
        given_steps=given,
        when_steps=when,
        then_steps=then,
        parent_requirement_id=req.id,
        decomposition_index=index,
    )


def _infer_steps(
    description: str, criteria: object
) -> tuple[list[str], list[str], list[str]]:
    """Infer Given/When/Then from a requirement description."""
    given: list[str] = []
    when: list[str] = []
    then: list[str] = []

    speed_match = re.search(r"(\d+)\s*kph", description)
    if speed_match:
        given.append(f"the host vehicle is travelling at {speed_match.group(1)} kph")

    if re.search(r"stationary\s+target", description, re.IGNORECASE):
        given.append("a stationary target is positioned ahead")

    if re.search(r"dry\s+(?:surface|pavement)", description, re.IGNORECASE):
        given.append("the road surface is dry (mu >= 0.85)")

    if re.search(r"forward\s+collision|threat", description, re.IGNORECASE):
        when.append("the forward collision threat is detected")

    if re.search(r"AEB|emergency\s+brak", description, re.IGNORECASE):
        when.append("the AEB system evaluates the collision risk")

    shall_matches = re.findall(r"shall\s+(.+?)(?:\.|,|$)", description, re.IGNORECASE)
    for match in shall_matches:
        then.append(match.strip()[:100])

    if not given:
        given.append("the system is in normal operating mode")
    if not when:
        when.append("the trigger condition is met")
    if not then:
        then.append("the system responds within specification")

    return given, when, then


def _infer_steps_from_clause(clause: str) -> tuple[list[str], list[str], list[str]]:
    """Infer Given/When/Then from a single clause of a compound requirement."""
    given: list[str] = []
    when: list[str] = []
    then: list[str] = []

    speed_match = re.search(r"(\d+)\s*kph", clause)
    if speed_match:
        given.append(f"the host vehicle is travelling at {speed_match.group(1)} kph")

    if re.search(r"stationary|slower.moving", clause, re.IGNORECASE):
        given.append("a target vehicle is detected ahead")

    if re.search(r"brake\s+command|braking", clause, re.IGNORECASE):
        when.append("the AEB brake command is initiated")
    elif re.search(r"threat|collision|warning", clause, re.IGNORECASE):
        when.append("a forward collision threat is detected")
    else:
        when.append("the trigger condition is met")

    shall_match = re.search(r"shall\s+(.+?)(?:\.|$)", clause, re.IGNORECASE)
    if shall_match:
        then.append(shall_match.group(1).strip()[:120])
    else:
        metric = re.search(r"(\d+(?:\.\d+)?)\s*(m/s\^2|ms|kph|m\b|s\b)", clause)
        if metric:
            then.append(f"the measured value meets the threshold of {metric.group(0)}")
        else:
            then.append(clause[:100])

    if not given:
        given.append("the system is in normal operating mode")

    return given, when, then


def _extract_short_title(clause: str) -> str:
    """Extract a short descriptive title from a clause."""
    keywords = {
        "deceleration": "deceleration",
        "warning": "warning",
        "lamp": "warning lamp",
        "haptic": "haptic alert",
        "ramp": "deceleration ramp",
        "display": "display",
        "braking": "braking",
        "stop": "stop distance",
    }
    for keyword, title in keywords.items():
        if keyword in clause.lower():
            return title
    return ""


def _slugify(text: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]+", " ", text).strip()


def format_scenarios(scenarios: list[GherkinScenario]) -> str:
    """Format a list of scenarios as a single Gherkin feature file."""
    if not scenarios:
        return ""

    lines: list[str] = []
    parent_id = scenarios[0].parent_requirement_id
    feature_name = scenarios[0].feature_name

    all_tags: set[str] = set()
    for s in scenarios:
        all_tags.update(t for t in s.tags if not t.startswith("decomposed-"))
    lines.append(" ".join(f"@{t}" for t in sorted(all_tags)))
    lines.append(f"Feature: {feature_name}")
    lines.append("")
    lines.append(f"  Decomposed from {parent_id} into {len(scenarios)} atomic scenarios.")
    lines.append("")

    for scenario in scenarios:
        scenario_tags = [t for t in scenario.tags if t.startswith("decomposed-")]
        if scenario_tags:
            lines.append("  " + " ".join(f"@{t}" for t in scenario_tags))
        lines.append(f"  Scenario: {scenario.scenario_name}")
        for step in scenario.given_steps:
            lines.append(f"    Given {step}")
        for step in scenario.when_steps:
            lines.append(f"    When {step}")
        for step in scenario.then_steps:
            lines.append(f"    Then {step}")
        lines.append("")

    return "\n".join(lines)
