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
