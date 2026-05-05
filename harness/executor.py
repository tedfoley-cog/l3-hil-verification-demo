"""Mock HIL test executor — replays pre-captured trace data.

Real dSPACE/NI HIL hardware is unreachable from a Devin VM. This executor
replays JSON trace files to produce the same signal DataFrame that a real
bench would, so downstream analysis (pass/fail, traceability, dashboard)
is identical. This is the "appears runnable" workaround per the playbook.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from harness.models import ExecutionResult, TestResult

_ROOT = Path(__file__).resolve().parent.parent
_TRACES_DIR = _ROOT / "traces"

# Map requirement patterns to trace files
_TRACE_MAP: dict[str, str] = {
    "REQ-SYS-AEB-001": "aeb_40kph_stationary.json",
    "REQ-SYS-AEB-002": "aeb_60kph_braking.json",
    "REQ-SYS-AEB-003": "aeb_40kph_stationary.json",
}


def load_trace(trace_file: str) -> dict[str, list[float]]:
    """Load a pre-captured trace from JSON."""
    path = _TRACES_DIR / trace_file
    if not path.exists():
        return {}
    with open(path) as f:
        data: dict[str, list[float]] = json.load(f)
    return data


def execute_test(
    test_id: str,
    requirement_id: str,
    scenario_name: str,
    bench_id: str = "bench_beta",
) -> ExecutionResult:
    """Execute a test against the mock HIL bench (replay harness)."""
    start_time = time.monotonic()

    trace_file = _TRACE_MAP.get(requirement_id, "aeb_40kph_stationary.json")
    trace = load_trace(trace_file)

    if not trace:
        return ExecutionResult(
            test_id=test_id,
            requirement_id=requirement_id,
            scenario_name=scenario_name,
            result=TestResult.ERROR,
            bench_id=bench_id,
            details=f"Trace file not found: {trace_file}",
        )

    metrics = _evaluate_trace(trace, requirement_id)
    result = _determine_verdict(metrics, requirement_id)
    duration_ms = (time.monotonic() - start_time) * 1000

    return ExecutionResult(
        test_id=test_id,
        requirement_id=requirement_id,
        scenario_name=scenario_name,
        result=result,
        metrics=metrics,
        duration_ms=duration_ms,
        bench_id=bench_id,
        trace_file=trace_file,
        details=_format_details(metrics, result),
    )


def _evaluate_trace(
    trace: dict[str, list[float]], requirement_id: str
) -> dict[str, float]:
    """Extract metrics from the trace data relevant to the requirement."""
    metrics: dict[str, float] = {}

    timestamps = trace.get("t", [])
    if not timestamps:
        return metrics

    vehicle_speed = trace.get("vehicle_speed_kph", [])
    if vehicle_speed:
        metrics["initial_speed_kph"] = vehicle_speed[0]
        metrics["final_speed_kph"] = vehicle_speed[-1]
        metrics["min_speed_kph"] = min(vehicle_speed)

    aeb_active = trace.get("aeb_brake_request", [])
    fcw_active = trace.get("fcw_active", [])
    if fcw_active and aeb_active:
        fcw_time = _first_activation_time(timestamps, fcw_active)
        aeb_time = _first_activation_time(timestamps, aeb_active)
        if fcw_time is not None and aeb_time is not None:
            metrics["fcw_activation_time_s"] = fcw_time
            metrics["aeb_activation_time_s"] = aeb_time
            metrics["aeb_response_time_ms"] = (aeb_time - fcw_time) * 1000

    decel = trace.get("deceleration_mps2", [])
    if decel:
        metrics["max_deceleration_mps2"] = max(decel)
        ramp_time = _ramp_time(timestamps, decel, threshold=6.0)
        if ramp_time is not None:
            metrics["decel_ramp_time_ms"] = ramp_time * 1000

    fcw_display = trace.get("cluster_fcw_lamp", [])
    if fcw_display and fcw_active:
        fcw_cmd_time = _first_activation_time(timestamps, fcw_active)
        display_time = _first_activation_time(timestamps, fcw_display)
        if fcw_cmd_time is not None and display_time is not None:
            metrics["fcw_display_latency_ms"] = (display_time - fcw_cmd_time) * 1000

    return metrics


def _first_activation_time(
    timestamps: list[float], signal: list[float]
) -> float | None:
    for t, v in zip(timestamps, signal):
        if v >= 0.5:
            return t
    return None


def _ramp_time(
    timestamps: list[float], signal: list[float], threshold: float
) -> float | None:
    start_time: float | None = None
    for t, v in zip(timestamps, signal):
        if v > 0.1 and start_time is None:
            start_time = t
        if v >= threshold and start_time is not None:
            return t - start_time
    return None


def _determine_verdict(metrics: dict[str, float], requirement_id: str) -> TestResult:
    """Determine pass/fail based on metrics and requirement thresholds."""
    if not metrics:
        return TestResult.ERROR

    if requirement_id == "REQ-SYS-AEB-001":
        response_time = metrics.get("aeb_response_time_ms")
        if response_time is not None and response_time <= 1200:
            return TestResult.PASS
        return TestResult.FAIL

    if requirement_id == "REQ-SYS-AEB-002":
        max_decel = metrics.get("max_deceleration_mps2", 0)
        ramp_time = metrics.get("decel_ramp_time_ms")
        fcw_latency = metrics.get("fcw_display_latency_ms")

        if max_decel >= 6.0 and ramp_time is not None and ramp_time <= 500:
            if fcw_latency is not None and fcw_latency <= 200:
                return TestResult.PASS
        return TestResult.FAIL

    if requirement_id == "REQ-SYS-AEB-003":
        fcw_latency = metrics.get("fcw_display_latency_ms")
        if fcw_latency is not None and fcw_latency <= 200:
            return TestResult.PASS
        return TestResult.FAIL

    return TestResult.PASS


def _format_details(metrics: dict[str, float], result: TestResult) -> str:
    lines = [f"Result: {result.value}"]
    for key, value in sorted(metrics.items()):
        lines.append(f"  {key}: {value:.2f}")
    return "\n".join(lines)
