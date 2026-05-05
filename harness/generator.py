"""Test artifact generator — Gherkin + signal mappings -> executable test script.

Produces Python test scripts in an ECU-TEST-inspired format, using the abstract
runner interface. Generated scripts never hard-code CAN signal IDs; instead they
reference the signal dictionary through the runner's abstraction API.
"""

from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from harness.models import GherkinScenario, SignalMapping, TestArtifact

_ROOT = Path(__file__).resolve().parent.parent
_TEMPLATE_DIR = _ROOT / "test_artifacts" / "templates"


def _get_jinja_env() -> Environment:
    return Environment(
        loader=FileSystemLoader(str(_TEMPLATE_DIR)),
        trim_blocks=True,
        lstrip_blocks=True,
    )


def generate_test_artifact(
    scenario: GherkinScenario,
    mappings: list[SignalMapping],
    bench_id: str = "bench_beta",
) -> TestArtifact:
    """Generate an executable test script from a scenario + signal mappings."""
    test_id = _make_test_id(scenario)

    env = _get_jinja_env()
    template = env.get_template("test_template.py.j2")

    script_content = template.render(
        test_id=test_id,
        scenario_name=scenario.scenario_name,
        feature_name=scenario.feature_name,
        requirement_id=scenario.parent_requirement_id,
        tags=scenario.tags,
        bench_id=bench_id,
        given_steps=scenario.given_steps,
        when_steps=scenario.when_steps,
        then_steps=scenario.then_steps,
        mappings=mappings,
        decomposition_index=scenario.decomposition_index,
    )

    return TestArtifact(
        test_id=test_id,
        scenario_name=scenario.scenario_name,
        requirement_id=scenario.parent_requirement_id,
        bench_id=bench_id,
        script_content=script_content,
        signal_mappings=mappings,
    )


def write_test_artifact(artifact: TestArtifact, output_dir: Path | None = None) -> Path:
    """Write a test artifact to disk."""
    out = output_dir or _ROOT / "test_artifacts" / "generated"
    out.mkdir(parents=True, exist_ok=True)
    filename = f"test_{artifact.test_id}.py"
    path = out / filename
    path.write_text(artifact.script_content)
    return path


def _make_test_id(scenario: GherkinScenario) -> str:
    """Generate a test ID from the scenario."""
    req_id = scenario.parent_requirement_id.lower().replace("-", "_")
    suffix = f"_{scenario.decomposition_index}" if scenario.decomposition_index > 0 else ""
    return f"{req_id}{suffix}"
