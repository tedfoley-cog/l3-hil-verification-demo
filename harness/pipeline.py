"""End-to-end V&V pipeline runner.

Processes a single requirement through every stage of the pipeline:

  1. Requirement Ingestion
  2. Quality Assessment (analyze)
  3. Scenario Decomposition
  4. Abstraction Mapping (bench-boundary)
  5. Test Artifact Generation
  6. Test Execution (replay harness)
  7. Impact Analysis
  8. Traceability Report

After each stage the dashboard state (``dashboard/state.json``) is updated so
the FastAPI dashboard reflects real-time progress.
"""

from __future__ import annotations

import json
from pathlib import Path

from harness.analyzer import analyze, load_requirement
from harness.decomposer import decompose, format_scenarios
from harness.executor import execute_test
from harness.generator import generate_test_artifact, write_test_artifact
from harness.mapper import AbstractionMapper
from harness.models import TestResult
from harness.tracer import build_traceability, save_traceability_report

_ROOT = Path(__file__).resolve().parent.parent
_STATE_FILE = _ROOT / "dashboard" / "state.json"

_STAGE_NAMES = [
    "Requirement Ingestion",
    "Quality Assessment",
    "Scenario Decomposition",
    "Abstraction Mapping",
    "Test Generation",
    "Test Execution",
    "Impact Analysis",
    "Traceability Report",
]


def _fresh_stages() -> list[dict[str, str]]:
    return [{"name": n, "status": "pending", "detail": ""} for n in _STAGE_NAMES]


def _update_state(patch: dict[str, object]) -> None:
    """Merge *patch* into the dashboard state file."""
    state: dict[str, object] = {}
    if _STATE_FILE.exists():
        with open(_STATE_FILE) as f:
            state = json.load(f)
    state.update(patch)
    with open(_STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)
        f.write("\n")


def _set_stage(
    stages: list[dict[str, str]], name: str, status: str, detail: str = ""
) -> None:
    for stage in stages:
        if stage["name"] == name:
            stage["status"] = status
            stage["detail"] = detail
            return


def run(requirement_path: str, bench_id: str = "bench_beta") -> int:
    """Execute the full V&V pipeline for a single requirement.

    Returns the number of failed tests (0 == all passed / nothing failed).
    """
    stages = _fresh_stages()
    _update_state(
        {
            "pipeline_stage": "running",
            "stages": stages,
            "requirements_analyzed": 0,
            "scenarios_generated": 0,
            "tests_generated": 0,
            "tests_executed": 0,
            "tests_passed": 0,
            "tests_failed": 0,
            "traceability_records": [],
        }
    )

    # Stage 1: Requirement Ingestion
    _set_stage(stages, "Requirement Ingestion", "running")
    _update_state({"stages": stages})
    req = load_requirement(requirement_path)
    _set_stage(stages, "Requirement Ingestion", "completed", f"Loaded {req.id}")
    _update_state({"stages": stages, "requirements_analyzed": 1})
    print(f"[1/8] Ingested: {req.id} — {req.title}")

    # Stage 2: Quality Assessment
    _set_stage(stages, "Quality Assessment", "running")
    _update_state({"stages": stages})
    assessment = analyze(req)
    _set_stage(
        stages,
        "Quality Assessment",
        "completed",
        f"Verdict: {assessment.verdict.value} | "
        f"{len(assessment.sub_requirements)} sub-requirements identified",
    )
    _update_state({"stages": stages})
    print(
        f"[2/8] Assessment: {assessment.verdict.value} — "
        f"atomic={assessment.is_atomic}, testable={assessment.is_testable}, "
        f"unambiguous={assessment.is_unambiguous}"
    )
    for issue in assessment.issues:
        print(f"       Issue: {issue}")

    # Stage 3: Scenario Decomposition
    _set_stage(stages, "Scenario Decomposition", "running")
    _update_state({"stages": stages})
    scenarios = decompose(req, assessment)
    _set_stage(
        stages,
        "Scenario Decomposition",
        "completed",
        f"Decomposed into {len(scenarios)} atomic scenarios",
    )
    _update_state({"stages": stages, "scenarios_generated": len(scenarios)})
    print(f"[3/8] Decomposed into {len(scenarios)} atomic scenarios:")
    for i, s in enumerate(scenarios, 1):
        print(f"       {i}. {s.scenario_name}")

    feature_text = format_scenarios(scenarios)
    feature_dir = _ROOT / "scenarios" / "generated"
    feature_dir.mkdir(parents=True, exist_ok=True)
    feature_path = feature_dir / f"{req.id.lower().replace('-', '_')}.feature"
    feature_path.write_text(feature_text)
    print(f"       Feature file: {feature_path.relative_to(_ROOT)}")

    # Stage 4: Abstraction Mapping
    _set_stage(stages, "Abstraction Mapping", "running")
    _update_state({"stages": stages})
    mapper = AbstractionMapper()
    all_mappings = [mapper.map_scenario(s, bench_id=bench_id) for s in scenarios]
    mapped_count = sum(
        1 for mappings in all_mappings for m in mappings if m.action_key != "unmapped"
    )
    total_steps = sum(len(m) for m in all_mappings)
    _set_stage(
        stages,
        "Abstraction Mapping",
        "completed",
        f"{mapped_count}/{total_steps} steps mapped for {bench_id}",
    )
    _update_state({"stages": stages})
    print(f"[4/8] Mapped {mapped_count}/{total_steps} steps through {bench_id}")

    # Stage 5: Test Generation
    _set_stage(stages, "Test Generation", "running")
    _update_state({"stages": stages})
    artifacts = []
    for scenario, mappings in zip(scenarios, all_mappings):
        artifact = generate_test_artifact(scenario, mappings, bench_id=bench_id)
        path = write_test_artifact(artifact)
        artifacts.append(artifact)
        print(f"[5/8] Generated: {path.relative_to(_ROOT)}")
    _set_stage(
        stages,
        "Test Generation",
        "completed",
        f"{len(artifacts)} test scripts generated",
    )
    _update_state({"stages": stages, "tests_generated": len(artifacts)})

    # Stage 6: Test Execution
    _set_stage(stages, "Test Execution", "running")
    _update_state({"stages": stages})
    results = []
    for artifact in artifacts:
        result = execute_test(
            test_id=artifact.test_id,
            requirement_id=artifact.requirement_id,
            scenario_name=artifact.scenario_name,
            bench_id=bench_id,
        )
        results.append(result)
        print(f"[6/8] Executed {artifact.test_id}: {result.result.value}")
        for k, v in sorted(result.metrics.items()):
            print(f"       {k}: {v:.2f}")
    passed = sum(1 for r in results if r.result == TestResult.PASS)
    failed = sum(1 for r in results if r.result == TestResult.FAIL)
    _set_stage(stages, "Test Execution", "completed", f"{passed} passed, {failed} failed")
    _update_state(
        {
            "stages": stages,
            "tests_executed": len(results),
            "tests_passed": passed,
            "tests_failed": failed,
        }
    )

    # Stage 7: Impact Analysis
    _set_stage(stages, "Impact Analysis", "running")
    _update_state({"stages": stages})
    existing_dir = _ROOT / "scenarios" / "existing"
    existing_affected: dict[str, list[str]] = {}
    if existing_dir.exists():
        affected = [
            f.stem
            for f in sorted(existing_dir.glob("*.feature"))
            if req.id in f.read_text()
        ]
        if affected:
            existing_affected[req.id] = affected
    affected_names = existing_affected.get(req.id, [])
    _set_stage(
        stages,
        "Impact Analysis",
        "completed",
        f"{len(affected_names)} existing scenario(s) may be affected",
    )
    _update_state({"stages": stages})
    if affected_names:
        print(f"[7/8] Impact: {len(affected_names)} existing scenario(s) may overlap:")
        for name in affected_names:
            print(f"       - {name}")
    else:
        print("[7/8] Impact: no existing scenario overlap detected")

    # Stage 8: Traceability Report
    _set_stage(stages, "Traceability Report", "running")
    _update_state({"stages": stages})
    records = build_traceability(scenarios, results, existing_affected)
    report_dir = _ROOT / "traces"
    md_path = save_traceability_report(records, report_dir, fmt="markdown")
    json_path = save_traceability_report(records, report_dir, fmt="json")
    print(f"[8/8] Traceability report: {md_path.relative_to(_ROOT)}")
    print(f"       JSON: {json_path.relative_to(_ROOT)}")

    trace_rows = [
        {
            "requirement_id": r.requirement_id,
            "requirement_title": r.requirement_title,
            "scenario_name": r.scenario_name,
            "test_id": r.test_id,
            "result": r.result.value,
            "bench_id": r.bench_id,
            "decomposed": r.decomposed,
            "impact_on_existing": r.impact_on_existing,
        }
        for r in records
    ]
    _set_stage(stages, "Traceability Report", "completed", "Report generated")
    _update_state(
        {
            "pipeline_stage": "completed",
            "stages": stages,
            "traceability_records": trace_rows,
        }
    )
    print("\nPipeline complete.")
    return failed


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(
        prog="vv-pipeline",
        description="Run the full V&V pipeline for a requirement",
    )
    parser.add_argument("path", help="Path to a requirement YAML file")
    parser.add_argument(
        "--bench",
        default="bench_beta",
        help="Bench configuration ID (default: bench_beta)",
    )
    args = parser.parse_args(argv)
    return run(args.path, bench_id=args.bench)


if __name__ == "__main__":
    raise SystemExit(main())
