"""Shared data models for the V&V pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class RequirementFormat(Enum):
    YAML = "yaml"
    GHERKIN = "gherkin"
    XLSX = "xlsx"


class QualityVerdict(Enum):
    ATOMIC = "atomic"
    COMPOUND = "compound"
    AMBIGUOUS = "ambiguous"
    UNTESTABLE = "untestable"


class TestResult(Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    NOT_RUN = "NOT_RUN"
    ERROR = "ERROR"


@dataclass
class AcceptanceCriterion:
    id: str
    text: str
    metric: str
    threshold: float
    type: str  # "analog" | "boolean"


@dataclass
class Requirement:
    id: str
    title: str
    description: str
    revision: int = 1
    status: str = "approved"
    asil: str = "QM"
    domain: str = ""
    subsystem: str = ""
    acceptance_criteria: list[AcceptanceCriterion] = field(default_factory=list)
    trace: dict[str, Any] = field(default_factory=dict)
    source_format: RequirementFormat = RequirementFormat.YAML
    source_path: str = ""


@dataclass
class QualityAssessment:
    requirement_id: str
    verdict: QualityVerdict
    is_atomic: bool
    is_testable: bool
    is_unambiguous: bool
    issues: list[str] = field(default_factory=list)
    sub_requirements: list[str] = field(default_factory=list)
    recommendation: str = ""


@dataclass
class GherkinScenario:
    """An atomic, testable Gherkin scenario decomposed from a requirement."""

    feature_name: str
    scenario_name: str
    tags: list[str] = field(default_factory=list)
    given_steps: list[str] = field(default_factory=list)
    when_steps: list[str] = field(default_factory=list)
    then_steps: list[str] = field(default_factory=list)
    parent_requirement_id: str = ""
    decomposition_index: int = 0

    def to_gherkin(self) -> str:
        lines: list[str] = []
        if self.tags:
            lines.append(" ".join(f"@{t}" for t in self.tags))
        lines.append(f"Feature: {self.feature_name}")
        lines.append("")
        lines.append(f"  Scenario: {self.scenario_name}")
        for step in self.given_steps:
            lines.append(f"    Given {step}")
        for step in self.when_steps:
            lines.append(f"    When {step}")
        for step in self.then_steps:
            lines.append(f"    Then {step}")
        lines.append("")
        return "\n".join(lines)


@dataclass
class SignalMapping:
    """Maps an abstract Gherkin step to concrete bench signal operations."""

    step_text: str
    action_key: str
    signals: list[dict[str, Any]] = field(default_factory=list)
    bench_id: str = ""
    ecu_routing: dict[str, str] = field(default_factory=dict)


@dataclass
class TestArtifact:
    """A generated executable test script."""

    test_id: str
    scenario_name: str
    requirement_id: str
    bench_id: str
    script_content: str = ""
    signal_mappings: list[SignalMapping] = field(default_factory=list)


@dataclass
class ExecutionResult:
    """Result of running a test artifact against the bench."""

    test_id: str
    requirement_id: str
    scenario_name: str
    result: TestResult = TestResult.NOT_RUN
    metrics: dict[str, float] = field(default_factory=dict)
    duration_ms: float = 0.0
    bench_id: str = ""
    trace_file: str = ""
    details: str = ""


@dataclass
class TraceabilityRecord:
    """Links requirement -> scenario -> test -> result."""

    requirement_id: str
    requirement_title: str
    scenario_name: str
    test_id: str
    result: TestResult = TestResult.NOT_RUN
    bench_id: str = ""
    decomposed: bool = False
    impact_on_existing: list[str] = field(default_factory=list)
