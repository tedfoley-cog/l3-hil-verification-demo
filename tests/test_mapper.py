"""Tests for the abstraction mapper."""

from __future__ import annotations

from harness.analyzer import analyze
from harness.decomposer import decompose
from harness.mapper import AbstractionMapper
from harness.models import Requirement


def test_map_atomic_scenario(atomic_requirement: Requirement) -> None:
    assessment = analyze(atomic_requirement)
    scenarios = decompose(atomic_requirement, assessment)
    mapper = AbstractionMapper()
    mappings = mapper.map_scenario(scenarios[0], bench_id="bench_beta")
    assert len(mappings) > 0
    mapped_count = sum(1 for m in mappings if m.action_key != "unmapped")
    assert mapped_count > 0


def test_bench_routing_differs() -> None:
    """Verify that bench_alpha and bench_beta produce different routing."""
    from harness.models import GherkinScenario

    scenario = GherkinScenario(
        feature_name="Test",
        scenario_name="routing test",
        given_steps=["the host vehicle is travelling at 40 kph"],
        when_steps=["a stationary target is detected at 80 m ahead"],
        then_steps=["the FCW warning icon is displayed"],
        parent_requirement_id="REQ-TEST",
    )
    mapper = AbstractionMapper()
    alpha = mapper.map_scenario(scenario, bench_id="bench_alpha")
    beta = mapper.map_scenario(scenario, bench_id="bench_beta")

    alpha_routing = {
        ecu: route
        for m in alpha
        for ecu, route in m.ecu_routing.items()
    }
    beta_routing = {
        ecu: route
        for m in beta
        for ecu, route in m.ecu_routing.items()
    }

    assert "Forward_Radar" not in alpha_routing or alpha_routing.get("Forward_Radar") == "real_bus"
    assert beta_routing.get("Forward_Radar") == "plant_model"


def test_signal_resolution_includes_can_ids(atomic_requirement: Requirement) -> None:
    assessment = analyze(atomic_requirement)
    scenarios = decompose(atomic_requirement, assessment)
    mapper = AbstractionMapper()
    mappings = mapper.map_scenario(scenarios[0])
    for m in mappings:
        if m.action_key != "unmapped":
            for sig in m.signals:
                assert sig.get("can_id") or sig.get("signal"), f"Signal missing ID: {sig}"


def test_speed_parameter_extraction() -> None:
    mapper = AbstractionMapper()
    action, params = mapper._match_action("the host vehicle is travelling at 60 kph")
    assert action == "set_vehicle_speed"
    assert params.get("speed_kph") == 60.0
