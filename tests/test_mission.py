"""Mission control tests."""

import time
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from alpha.telemetry_aggregator import (
    TelemetryAggregator, TelemetryPoint, MetricDefinition, MetricType, SourceType,
)
from omega.mission_orchestrator import (
    MissionOrchestrator, MissionPhase, PhaseTransition, SubsystemAction,
    create_f9_mission,
)


def test_aggregator_ingest():
    agg = TelemetryAggregator()
    point = TelemetryPoint("vehicle", "altitude", 100.0, time.time())
    assert agg.ingest(point)
    assert len(agg._buffer) == 1


def test_aggregator_metric_stats():
    agg = TelemetryAggregator()
    agg.define_metric(MetricDefinition("altitude", MetricType.GAUGE, "m"))
    for i in range(10):
        agg.ingest(TelemetryPoint("v", "altitude", float(i * 100), time.time()))

    metric = agg.get_metric("altitude")
    assert metric is not None
    assert metric.count == 10
    assert metric.mean == 450.0


def test_aggregator_query():
    agg = TelemetryAggregator()
    for i in range(5):
        agg.ingest(TelemetryPoint("v", "altitude", float(i), time.time()))

    results = agg.query(metric="altitude", limit=3)
    assert len(results) == 3


def test_aggregator_time_series():
    agg = TelemetryAggregator()
    for i in range(10):
        agg.ingest(TelemetryPoint("v", "velocity", float(i * 100), time.time()))

    ts = agg.get_time_series("velocity", 1.0)
    assert len(ts) > 0


def test_aggregator_derivative():
    agg = TelemetryAggregator()
    t = time.time()
    agg.ingest(TelemetryPoint("v", "altitude", 100.0, t))
    agg.ingest(TelemetryPoint("v", "altitude", 200.0, t + 10))

    rate = agg.compute_derivative("altitude", 15.0)
    assert abs(rate - 10.0) < 0.1


def test_aggregator_source_health():
    agg = TelemetryAggregator()
    agg.register_source("vehicle", SourceType.VEHICLE)
    agg.ingest(TelemetryPoint("vehicle", "alt", 100, time.time()))

    health = agg.source_health
    assert health["vehicle"]["status"] == "HEALTHY"


def test_orchestrator_lifecycle():
    orch = MissionOrchestrator()
    assert orch.phase == MissionPhase.PRE_LAUNCH

    orch.transition_to(MissionPhase.COUNTDOWN, "auto")
    assert orch.phase == MissionPhase.COUNTDOWN

    orch.transition_to(MissionPhase.LIFTOFF)
    assert orch.phase == MissionPhase.LIFTOFF


def test_orchestrator_transition_callbacks():
    orch = MissionOrchestrator()
    phases_seen = []
    orch.on_phase(MissionPhase.COUNTDOWN, lambda d: phases_seen.append("countdown"))

    orch.transition_to(MissionPhase.COUNTDOWN)
    assert "countdown" in phases_seen


def test_orchestrator_abort():
    orch = MissionOrchestrator()
    orch.transition_to(MissionPhase.COUNTDOWN)
    orch.abort("manual test")
    assert orch.phase == MissionPhase.ABORT
    assert not orch.transition_to(MissionPhase.LIFTOFF)


def test_orchestrator_subsystem_action():
    orch = MissionOrchestrator()
    executed = []
    orch.add_action(SubsystemAction(
        MissionPhase.LIFTOFF, "engines", lambda: executed.append(True)
    ))

    orch.transition_to(MissionPhase.LIFTOFF)
    assert len(executed) == 1


def test_orchestrator_auto_transition():
    orch = MissionOrchestrator()
    orch.add_transition(PhaseTransition(
        MissionPhase.PRE_LAUNCH, MissionPhase.COUNTDOWN,
        lambda: True, "auto_start"
    ))

    result = orch.check_transitions()
    assert result == MissionPhase.COUNTDOWN


def test_orchestrator_event_log():
    orch = MissionOrchestrator()
    orch.transition_to(MissionPhase.COUNTDOWN)
    orch.transition_to(MissionPhase.LIFTOFF)

    log = orch.event_log
    assert len(log) >= 2


def test_f9_mission_config():
    orch = MissionOrchestrator()
    create_f9_mission(orch)
    assert len(orch._transitions) >= 10


def test_dashboard_summary():
    agg = TelemetryAggregator()
    agg.define_metric(MetricDefinition("alt", MetricType.GAUGE, "m"))
    summary = agg.dashboard_summary
    assert summary["total_metrics"] == 1


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = failed = 0
    for t in tests:
        try:
            t()
            print(f"  PASS  {t.__name__}")
            passed += 1
        except Exception as e:
            print(f"  FAIL  {t.__name__}: {e}")
            failed += 1
    print(f"\n{passed} passed, {failed} failed")
    sys.exit(1 if failed else 0)
