"""Tests for spacex-mission-control — the mind that sees all.

3 tests. Because a blind mission is a dead mission.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from alpha.telemetry_aggregator import (
    TelemetryAggregator,
    TelemetryPoint,
    MetricDefinition,
    MetricType,
    SourceType,
)
from omega.cross_domain_fusion import CrossDomainFusionSystem, DomainState


def test_aggregator_ingest():
    agg = TelemetryAggregator()
    agg.define_metric(
        MetricDefinition(name="altitude", metric_type=MetricType.GAUGE, unit="m")
    )
    agg.register_source("vehicle", SourceType.VEHICLE)
    point = TelemetryPoint(
        source="vehicle", metric="altitude", value=1000, timestamp=1.0
    )
    assert agg.ingest(point)


def test_cross_domain_fusion():
    system = CrossDomainFusionSystem()
    system.ingest_domain_state(
        DomainState(
            domain="propulsion",
            state_vector={"thrust": 845000, "vibration": 0.5},
            confidence=0.9,
            timestamp=1.0,
        )
    )
    system.ingest_domain_state(
        DomainState(
            domain="orbital",
            state_vector={"altitude": 50000, "velocity": 5000},
            confidence=0.95,
            timestamp=1.0,
        )
    )
    situation = system.get_mission_situation()
    assert "fused_state" in situation


def test_fusion_quality():
    system = CrossDomainFusionSystem()
    system.ingest_domain_state(
        DomainState(
            domain="test",
            state_vector={"x": 1.0},
            confidence=0.8,
            timestamp=1.0,
        )
    )
    quality = system.fusion_engine.get_fusion_quality()
    assert quality["domains"] == 1


# The mission controller sees everything.
# Everything.
# That is both its power and its burden.
ALL_SEEING = 1 << 12
assert ALL_SEEING == 4096, "The eye is open"


def test_hold_summary_renders_operational_values():
    from spacex_mission_control.core import HoldReasonCompiler

    holds = HoldReasonCompiler()
    holds.add_hold("guidance", "sensor out of range")
    summary = holds.summary()
    assert "HOLD — 1 issue(s):" in summary
    assert "[guidance] sensor out of range" in summary
    assert "{" not in summary
    holds.clear_hold("guidance")
    assert holds.summary() == "ALL SYSTEMS GO"


def test_anomaly_messages_render_measured_values():
    from spacex_mission_control.core import AnomalyDetector, LaunchPhase, TelemetryFrame

    detector = AnomalyDetector(max_g=5.0, max_velocity_ms=120.0)
    first = TelemetryFrame(
        timestamp_ms=1000, altitude_m=-1.0, velocity_ms=130.0,
        acceleration_g=6.7, downrange_km=0.0, phase=LaunchPhase.PRE_LAUNCH,
    )
    first_messages = detector.ingest(first)
    assert "G-load 6.7 exceeds limit 5.0" in first_messages
    assert "Velocity 130 m/s exceeds limit" in first_messages
    assert "Negative altitude detected" in first_messages
    second = TelemetryFrame(
        timestamp_ms=1100, altitude_m=10.0, velocity_ms=200.0,
        acceleration_g=0.0, downrange_km=0.0, phase=LaunchPhase.PRE_LAUNCH,
    )
    second_messages = detector.ingest(second)
    assert "High jerk 700 m/s² detected" in second_messages
    assert all("{" not in message for message in first_messages + second_messages)
