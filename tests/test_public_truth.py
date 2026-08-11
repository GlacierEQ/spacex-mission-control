from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from omega.mission_orchestrator import (
    EVIDENCE_STATE,
    MissionOrchestrator,
    create_demo_mission,
    create_f9_mission,
)


def test_demo_profile_is_canonical_and_historical_alias_is_equivalent() -> None:
    demo = MissionOrchestrator()
    historical = MissionOrchestrator()
    create_demo_mission(demo)
    create_f9_mission(historical)
    assert len(demo._transitions) == len(historical._transitions)
    assert len(demo._transitions) >= 10


def test_summary_and_events_emit_simulation_evidence_state() -> None:
    orchestrator = MissionOrchestrator()
    create_demo_mission(orchestrator)
    orchestrator.check_transitions()
    assert orchestrator.mission_summary["evidence_state"] == EVIDENCE_STATE
    assert orchestrator.event_log[-1]["evidence_state"] == EVIDENCE_STATE
    assert orchestrator.mission_elapsed >= orchestrator.phase_elapsed


def test_machine_truth_matches_local_simulation_scope() -> None:
    capabilities = json.loads((ROOT / "machine/capabilities.json").read_text())
    target = json.loads((ROOT / "machine/target-contract.json").read_text())
    assert "hyper-scaling" not in capabilities["capabilities"]
    assert target["current"]["deployed"] is False
    assert target["verified_capability"] == (
        "deterministic-local-mission-operations-simulation"
    )
    assert target["evidence_token"] == EVIDENCE_STATE
