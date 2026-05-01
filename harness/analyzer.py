"""Requirement quality assessment — atomic? testable? unambiguous?

Examines a requirement and determines whether it is suitable for direct
test generation or needs decomposition first. This is the first stage of
the V&V pipeline.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from harness.models import (
    AcceptanceCriterion,
    QualityAssessment,
    QualityVerdict,
    Requirement,
    RequirementFormat,
)

# Conjunctions that suggest a compound requirement.
# The first pattern specifically requires two separate "shall" clauses
# connected by "and" — a single "shall" with "and" in a subordinate clause
# (e.g. "provided the driver has not applied") is NOT compound.
_COMPOUND_MARKERS = [
    r"\bshall\b.*,\s*and\s+the\b.*\bshall\b",
    r",\s*and\s+the\s+\w+\s+shall\b",
    r"\badditionally\b",
    r"\bfurthermore\b",
    r"\bmoreover\b",
    r"\bas well as\b.*\bshall\b",
]

# Phrases that suggest ambiguity
_AMBIGUITY_MARKERS = [
    r"\bappropriate\b",
    r"\breasonable\b",
    r"\bsufficient\b",
    r"\badequate\b",
    r"\bas needed\b",
    r"\bif necessary\b",
    r"\bnormally\b",
    r"\btypically\b",
    r"\bgenerally\b",
    r"\betc\.?\b",
]

# Phrases that suggest untestability
_UNTESTABLE_MARKERS = [
    r"\buser[- ]friendly\b",
    r"\bintuitive\b",
    r"\brobust\b",
    r"\bscalable\b",
    r"\bperformant\b",
    r"\bhigh[- ]quality\b",
]


def load_requirement(path: str | Path) -> Requirement:
    """Load a requirement from a YAML file."""
    p = Path(path)
    with open(p) as f:
        data: dict[str, Any] = yaml.safe_load(f)

    criteria = [
        AcceptanceCriterion(
            id=ac["id"],
            text=ac["text"],
            metric=ac.get("metric", ""),
            threshold=float(ac.get("threshold", 0)),
            type=ac.get("type", "boolean"),
        )
        for ac in data.get("acceptance_criteria", [])
    ]

    return Requirement(
        id=data["id"],
        title=data.get("title", ""),
        description=data.get("description", ""),
        revision=int(data.get("revision", 1)),
        status=data.get("status", "approved"),
        asil=data.get("asil", "QM"),
        domain=data.get("domain", ""),
        subsystem=data.get("subsystem", ""),
        acceptance_criteria=criteria,
        trace=data.get("trace", {}),
        source_format=RequirementFormat.YAML,
        source_path=str(p),
    )


def _count_shall_clauses(text: str) -> int:
    return len(re.findall(r"\bshall\b", text, re.IGNORECASE))


def _find_markers(text: str, patterns: list[str]) -> list[str]:
    found: list[str] = []
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        found.extend(matches)
    return found


def analyze(requirement: Requirement) -> QualityAssessment:
    """Assess whether a requirement is atomic, testable, and unambiguous."""
    desc = requirement.description
    issues: list[str] = []
    sub_requirements: list[str] = []

    shall_count = _count_shall_clauses(desc)
    compound_hits = _find_markers(desc, _COMPOUND_MARKERS)
    ambiguity_hits = _find_markers(desc, _AMBIGUITY_MARKERS)
    untestable_hits = _find_markers(desc, _UNTESTABLE_MARKERS)

    is_atomic = shall_count <= 1 and len(compound_hits) == 0
    is_testable = len(untestable_hits) == 0 and len(requirement.acceptance_criteria) > 0
    is_unambiguous = len(ambiguity_hits) == 0

    if not is_atomic:
        issues.append(
            f"Compound requirement: found {shall_count} 'shall' clauses "
            f"and {len(compound_hits)} compound markers."
        )
        sub_requirements = _extract_sub_requirements(desc)

    if not is_testable:
        if untestable_hits:
            issues.append(f"Untestable language: {', '.join(untestable_hits)}")
        if not requirement.acceptance_criteria:
            issues.append("No acceptance criteria defined.")

    if not is_unambiguous:
        issues.append(f"Ambiguous language: {', '.join(ambiguity_hits)}")

    if is_atomic and is_testable and is_unambiguous:
        verdict = QualityVerdict.ATOMIC
        recommendation = "Requirement is ready for test generation."
    elif not is_atomic:
        verdict = QualityVerdict.COMPOUND
        recommendation = (
            f"Decompose into {len(sub_requirements)} atomic scenarios "
            "before generating tests."
        )
    elif not is_testable:
        verdict = QualityVerdict.UNTESTABLE
        recommendation = "Refine requirement with measurable acceptance criteria."
    else:
        verdict = QualityVerdict.AMBIGUOUS
        recommendation = "Clarify ambiguous language before test generation."

    return QualityAssessment(
        requirement_id=requirement.id,
        verdict=verdict,
        is_atomic=is_atomic,
        is_testable=is_testable,
        is_unambiguous=is_unambiguous,
        issues=issues,
        sub_requirements=sub_requirements,
        recommendation=recommendation,
    )


def _extract_sub_requirements(description: str) -> list[str]:
    """Split a compound description into candidate sub-requirements."""
    parts: list[str] = []
    conjunctions = re.split(r",\s*and\s+the\b|\band\s+the\b", description, flags=re.IGNORECASE)
    for part in conjunctions:
        part = part.strip()
        if part and len(part) > 20:
            if not re.match(r"(?i)^the\b", part):
                part = "The system " + part
            parts.append(part)
    return parts if len(parts) > 1 else [description]


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for analyzing a single requirement."""
    import argparse
    import json

    parser = argparse.ArgumentParser(
        prog="requirement-analyzer",
        description="Assess requirement quality (atomic? testable? unambiguous?)",
    )
    parser.add_argument("path", help="Path to a YAML requirement file")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args(argv)

    req = load_requirement(args.path)
    assessment = analyze(req)

    if args.json:
        import dataclasses

        print(json.dumps(dataclasses.asdict(assessment), indent=2, default=str))
    else:
        print(f"Requirement: {req.id} — {req.title}")
        print(f"  Verdict:      {assessment.verdict.value}")
        print(f"  Atomic:       {assessment.is_atomic}")
        print(f"  Testable:     {assessment.is_testable}")
        print(f"  Unambiguous:  {assessment.is_unambiguous}")
        if assessment.issues:
            print("  Issues:")
            for issue in assessment.issues:
                print(f"    - {issue}")
        if assessment.sub_requirements:
            print(f"  Sub-requirements ({len(assessment.sub_requirements)}):")
            for i, sub in enumerate(assessment.sub_requirements, 1):
                preview = sub[:80] + "..." if len(sub) > 80 else sub
                print(f"    {i}. {preview}")
        print(f"  Recommendation: {assessment.recommendation}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
