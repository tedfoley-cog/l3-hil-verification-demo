"""Abstraction mapper — translates Gherkin steps through the action library.

Takes abstract Gherkin steps (e.g. "the host vehicle is travelling at 40 kph")
and maps them through the action library + signal dictionary + bench boundary
to produce concrete signal-level operations for a specific bench configuration.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import yaml

from harness.models import GherkinScenario, SignalMapping

_ROOT = Path(__file__).resolve().parent.parent


def _load_yaml(path: Path) -> dict[str, Any]:
    with open(path) as f:
        data: Any = yaml.safe_load(f)
    return data if isinstance(data, dict) else {}


def _load_json(path: Path) -> dict[str, Any]:
    with open(path) as f:
        data: Any = json.load(f)
    return data if isinstance(data, dict) else {}


class AbstractionMapper:
    """Maps abstract Gherkin steps to concrete bench signal operations."""

    def __init__(
        self,
        action_library_path: Path | None = None,
        signal_dict_path: Path | None = None,
        bench_boundary_path: Path | None = None,
    ):
        self.actions = _load_yaml(
            action_library_path or _ROOT / "abstraction" / "action_library.yaml"
        )
        self.signals = _load_yaml(
            signal_dict_path or _ROOT / "abstraction" / "signal_dictionary.yaml"
        )
        self.bench_boundary = _load_yaml(
            bench_boundary_path or _ROOT / "abstraction" / "bench_boundary.yaml"
        )

    def load_bench_config(self, bench_id: str) -> dict[str, Any]:
        path = _ROOT / "bench_configs" / f"{bench_id}.json"
        if path.exists():
            return _load_json(path)
        return {}

    def map_scenario(
        self, scenario: GherkinScenario, bench_id: str = "bench_beta"
    ) -> list[SignalMapping]:
        """Map all steps in a scenario to signal operations for the given bench."""
        bench = self.load_bench_config(bench_id)
        bench_boundary = self.bench_boundary.get("benches", {}).get(bench_id, {})
        ecu_map = bench_boundary.get("ecus", {})

        mappings: list[SignalMapping] = []
        all_steps = (
            [(s, "given") for s in scenario.given_steps]
            + [(s, "when") for s in scenario.when_steps]
            + [(s, "then") for s in scenario.then_steps]
        )

        for step_text, _phase in all_steps:
            action_key, params = self._match_action(step_text)
            if action_key and action_key in self.actions:
                action_def = self.actions[action_key]
                resolved_signals = self._resolve_signals(
                    action_def.get("signals", []), params, ecu_map, bench
                )
                ecu_routing = self._determine_routing(resolved_signals, ecu_map)
                mappings.append(
                    SignalMapping(
                        step_text=step_text,
                        action_key=action_key,
                        signals=resolved_signals,
                        bench_id=bench_id,
                        ecu_routing=ecu_routing,
                    )
                )
            else:
                mappings.append(
                    SignalMapping(
                        step_text=step_text,
                        action_key="unmapped",
                        signals=[],
                        bench_id=bench_id,
                        ecu_routing={},
                    )
                )

        return mappings

    def _match_action(self, step_text: str) -> tuple[str | None, dict[str, float]]:
        """Match a Gherkin step to an action library key + extracted parameters."""
        text = step_text.lower()
        params: dict[str, float] = {}

        speed_match = re.search(r"(\d+(?:\.\d+)?)\s*kph", text)
        if speed_match:
            params["speed_kph"] = float(speed_match.group(1))

        force_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:n\b|newton)", text)
        if force_match:
            params["force_n"] = float(force_match.group(1))

        range_match = re.search(r"(\d+(?:\.\d+)?)\s*m\s+ahead", text)
        if range_match:
            params["range_m"] = float(range_match.group(1))

        decel_match = re.search(r"(\d+(?:\.\d+)?)\s*m/s\^?2", text)
        if decel_match:
            params["decel_mps2"] = float(decel_match.group(1))

        time_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:ms|millisecond)", text)
        if time_match:
            params["time_ms"] = float(time_match.group(1))

        if "travelling at" in text or "traveling at" in text:
            return "set_vehicle_speed", params
        if "ignition" in text and ("run" in text or "on" in text):
            return "set_ignition_on", params
        if "ignition" in text and "off" in text:
            return "set_ignition_off", params
        if "brake pedal" in text and ("apply" in text or "force" in text or "exceeds" in text):
            return "apply_brake_pedal", params
        if "not applying" in text and "brake" in text:
            return "release_brake_pedal", params
        if "stationary target" in text and ("positioned" in text or "detected" in text):
            return "inject_radar_target", params
        if "target" in text and "detected" in text and "ahead" in text:
            return "inject_radar_target", params
        if "collision" in text and ("warning" in text or "threat" in text):
            return "trigger_fcw", params
        if "aeb" in text and ("initiate" in text or "brake" in text or "activat" in text):
            return "trigger_aeb", params
        if "complete stop" in text or "stopped" in text:
            return "check_vehicle_stopped", params
        if "fcw" in text and ("display" in text or "icon" in text or "lamp" in text):
            return "check_fcw_display", params
        if "haptic" in text:
            return "check_haptic_alert", params
        if "decelerat" in text:
            return "trigger_aeb", params

        return None, params

    def _resolve_signals(
        self,
        action_signals: list[dict[str, Any]],
        params: dict[str, float],
        ecu_map: dict[str, Any],
        bench: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Resolve abstract signal references to concrete signal definitions."""
        resolved: list[dict[str, Any]] = []
        simulated_ecus: list[str] = bench.get("simulated_ecus", [])

        for sig_def in action_signals:
            signal_name = sig_def.get("signal", "")
            signal_info = self.signals.get(signal_name, {})

            value = sig_def.get("value")
            if value == "parameter":
                if "speed_kph" in params and "speed" in signal_name:
                    value = params["speed_kph"]
                elif "force_n" in params and "force" in signal_name:
                    value = params["force_n"]
                elif "range_m" in params and "range" in signal_name:
                    value = params["range_m"]
                elif "decel_mps2" in params and "decel" in signal_name:
                    value = params["decel_mps2"]
                else:
                    value = 0

            ecu = signal_info.get("ecu", "unknown")
            is_simulated = ecu in simulated_ecus

            resolved.append(
                {
                    "signal": signal_name,
                    "value": value,
                    "can_id": signal_info.get("can_id", ""),
                    "bus": signal_info.get("bus", ""),
                    "unit": signal_info.get("unit", ""),
                    "ecu": ecu,
                    "routing": "plant_model" if is_simulated else "real_bus",
                    "delay_ms": sig_def.get("delay_ms", 0),
                }
            )

        return resolved

    def _determine_routing(
        self, signals: list[dict[str, Any]], ecu_map: dict[str, Any]
    ) -> dict[str, str]:
        """Determine routing (real bus vs plant model) for each signal's ECU."""
        routing: dict[str, str] = {}
        for sig in signals:
            ecu = sig.get("ecu", "unknown")
            ecu_info = ecu_map.get(ecu, {})
            ecu_type = ecu_info.get("type", "unknown")
            routing[ecu] = "plant_model" if ecu_type == "simulated" else "real_bus"
        return routing
