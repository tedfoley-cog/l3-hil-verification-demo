"""Traceability matrix — requirement -> scenario -> test -> result.

Builds and formats the traceability report that links every test result
back to its originating requirement, through the decomposed scenario.
This is the final output artifact of the V&V pipeline.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from harness.models import ExecutionResult, GherkinScenario, TestResult, TraceabilityRecord


def build_traceability(
    scenarios: list[GherkinScenario],
    results: list[ExecutionResult],
    existing_affected: dict[str, list[str]] | None = None,
) -> list[TraceabilityRecord]:
    """Build traceability records linking requirements to test results."""
    result_map = {r.test_id: r for r in results}
    records: list[TraceabilityRecord] = []

    for scenario in scenarios:
        req_id = scenario.parent_requirement_id
        test_id = _scenario_to_test_id(scenario)
        exec_result = result_map.get(test_id)

        record = TraceabilityRecord(
            requirement_id=req_id,
            requirement_title=scenario.feature_name,
            scenario_name=scenario.scenario_name,
            test_id=test_id,
            result=exec_result.result if exec_result else TestResult.NOT_RUN,
            bench_id=exec_result.bench_id if exec_result else "",
            decomposed=scenario.decomposition_index > 0,
            impact_on_existing=(existing_affected or {}).get(req_id, []),
        )
        records.append(record)

    return records


def format_traceability_markdown(records: list[TraceabilityRecord]) -> str:
    """Format traceability records as a Markdown table."""
    lines = [
        "# Traceability Report",
        "",
        "| Requirement | Scenario | Test ID | Result | Bench | Decomposed | Impact |",
        "|---|---|---|---|---|---|---|",
    ]

    for r in records:
        impact = ", ".join(r.impact_on_existing) if r.impact_on_existing else "—"
        result_icon = _result_icon(r.result)
        lines.append(
            f"| {r.requirement_id} | {r.scenario_name[:40]} | {r.test_id} "
            f"| {result_icon} {r.result.value} | {r.bench_id} "
            f"| {'Yes' if r.decomposed else 'No'} | {impact} |"
        )

    # Summary
    total = len(records)
    passed = sum(1 for r in records if r.result == TestResult.PASS)
    failed = sum(1 for r in records if r.result == TestResult.FAIL)
    not_run = sum(1 for r in records if r.result == TestResult.NOT_RUN)
    errors = sum(1 for r in records if r.result == TestResult.ERROR)
    decomposed = sum(1 for r in records if r.decomposed)

    lines.extend([
        "",
        "## Summary",
        "",
        f"- **Total scenarios**: {total}",
        f"- **Passed**: {passed}",
        f"- **Failed**: {failed}",
        f"- **Not run**: {not_run}",
        f"- **Errors**: {errors}",
        f"- **Decomposed from compound requirements**: {decomposed}",
    ])

    return "\n".join(lines)


def format_traceability_json(records: list[TraceabilityRecord]) -> str:
    """Format traceability records as JSON."""
    data = [asdict(r) for r in records]
    for d in data:
        d["result"] = d["result"].value if hasattr(d["result"], "value") else str(d["result"])
    return json.dumps(data, indent=2)


def save_traceability_report(
    records: list[TraceabilityRecord],
    output_dir: Path,
    fmt: str = "markdown",
) -> Path:
    """Save the traceability report to disk."""
    output_dir.mkdir(parents=True, exist_ok=True)
    if fmt == "json":
        path = output_dir / "traceability_report.json"
        path.write_text(format_traceability_json(records))
    else:
        path = output_dir / "traceability_report.md"
        path.write_text(format_traceability_markdown(records))
    return path


def _scenario_to_test_id(scenario: GherkinScenario) -> str:
    req_id = scenario.parent_requirement_id.lower().replace("-", "_")
    suffix = f"_{scenario.decomposition_index}" if scenario.decomposition_index > 0 else ""
    return f"{req_id}{suffix}"


def _result_icon(result: TestResult) -> str:
    return {
        TestResult.PASS: "PASS",
        TestResult.FAIL: "FAIL",
        TestResult.NOT_RUN: "SKIP",
        TestResult.ERROR: "ERR",
    }.get(result, "?")
