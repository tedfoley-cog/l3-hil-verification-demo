"""Shared fixtures for the test suite."""

from __future__ import annotations

from pathlib import Path

import pytest

from harness.models import AcceptanceCriterion, Requirement, RequirementFormat

_REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture()
def repo_root() -> Path:
    return _REPO_ROOT


@pytest.fixture()
def atomic_requirement() -> Requirement:
    return Requirement(
        id="REQ-SYS-AEB-001",
        title="AEB activation timing for stationary target",
        description=(
            "When the host vehicle approaches a stationary target at speeds between "
            "30 kph and 80 kph on a dry surface (mu >= 0.85), the Automatic Emergency "
            "Braking system shall initiate autonomous braking no later than 1.2 seconds "
            "after the forward collision warning is issued, provided the driver has not "
            "applied the brake pedal."
        ),
        revision=4,
        asil="C",
        domain="ADAS",
        subsystem="Forward Collision Mitigation",
        acceptance_criteria=[
            AcceptanceCriterion(
                id="AC-001-1",
                text="AEB brake command is issued within 1200 ms of FCW activation",
                metric="aeb_response_time_ms",
                threshold=1200,
                type="analog",
            ),
        ],
        trace={"parent": "REQ-VEH-FCM-010"},
        source_format=RequirementFormat.YAML,
    )


@pytest.fixture()
def compound_requirement() -> Requirement:
    return Requirement(
        id="REQ-SYS-AEB-002",
        title="AEB deceleration profile and warning coordination",
        description=(
            "The AEB system shall apply a minimum deceleration of 6 m/s^2 within "
            "500 ms of brake command initiation when the host vehicle is travelling "
            "between 30 kph and 80 kph toward a stationary or slower-moving target, "
            "and the forward collision warning shall illuminate the instrument cluster "
            "warning lamp within 200 ms of threat detection, and the haptic seat alert "
            "shall activate simultaneously with the visual warning, and the AEB "
            "deceleration shall ramp to full braking (>= 9.5 m/s^2) within 1.0 second "
            "of initial brake application if the collision is not averted."
        ),
        revision=2,
        asil="C",
        domain="ADAS",
        subsystem="Forward Collision Mitigation",
        acceptance_criteria=[
            AcceptanceCriterion(
                id="AC-002-1",
                text="All conditions met during a 40 kph approach",
                metric="compound_pass",
                threshold=1,
                type="boolean",
            ),
        ],
        trace={"parent": "REQ-VEH-FCM-012"},
        source_format=RequirementFormat.YAML,
    )
