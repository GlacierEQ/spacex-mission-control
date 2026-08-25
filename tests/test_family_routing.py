from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "compose_family_receipts.py"
spec = importlib.util.spec_from_file_location("compose_family_receipts", MODULE_PATH)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def digest(body: dict) -> str:
    raw = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def receipt(schema: str, capability: str) -> dict:
    body = {
        "schema": schema,
        "selection_mode": "CURRENT_BEST_REVISABLE",
        "capability": capability,
        "evidence_state": "TEST_EVIDENCE",
        "external_actions_executed": 0,
    }
    return {**body, "receipt_sha256": digest(body)}


def routing() -> dict:
    return module.load_routing(ROOT / "machine" / "family-routing.json")


def test_plan_exposes_all_initial_wired_specialists() -> None:
    plan = module.build_plan(routing())
    assert plan["family_id"] == "FAM-SPACEX"
    assert plan["head_repository"] == "GlacierEQ/spacex-mission-control"
    assert plan["parallelizable"] is True
    assert {row["repository"] for row in plan["members"]} == {
        "GlacierEQ/spacex-propulsion-monitor",
        "GlacierEQ/spacex-pad-weather-gate",
        "GlacierEQ/spacex-launch-sequencer",
        "GlacierEQ/spacex-orbital-mechanics",
    }
    assert len(plan["plan_sha256"]) == 64


def test_composition_preserves_specialist_identity_and_capability() -> None:
    result = module.compose(
        [
            receipt("glaciereq.health-operate-receipt.v1", "deterministic-local-multi-sensor-health-evaluation"),
            receipt("glaciereq.weather-operate-receipt.v1", "deterministic-local-environmental-constraint-evaluation"),
            receipt("glaciereq.countdown-operate-receipt.v1", "deterministic-local-countdown-orchestration"),
            receipt("glaciereq.orbital-operate-receipt.v1", "repository-native-lambert-two-body"),
        ],
        routing(),
    )
    assert result["status"] == "PASS"
    assert result["member_count"] == 4
    assert result["capability_truth_privilege"] is False
    assert len(result["composed_capabilities"]) == 4
    assert len(result["receipt_sha256"]) == 64


def test_tampered_receipt_is_rejected() -> None:
    payload = receipt("glaciereq.health-operate-receipt.v1", "deterministic-local-multi-sensor-health-evaluation")
    payload["evidence_state"] = "TAMPERED"
    try:
        module.compose([payload], routing())
    except ValueError as exc:
        assert "hash mismatch" in str(exc)
    else:
        raise AssertionError("tampered receipt was accepted")


def test_unregistered_receipt_schema_is_rejected() -> None:
    payload = receipt("glaciereq.unknown-receipt.v1", "unknown")
    try:
        module.compose([payload], routing())
    except ValueError as exc:
        assert "unregistered specialist receipt schema" in str(exc)
    else:
        raise AssertionError("unknown family member was accepted")


def test_head_never_gains_capability_truth_privilege() -> None:
    cfg = routing()
    cfg["capability_truth_privilege"] = True
    try:
        module.verify_member_receipt(
            receipt("glaciereq.health-operate-receipt.v1", "deterministic-local-multi-sensor-health-evaluation"),
            cfg,
        )
    except ValueError as exc:
        assert "capability truth privilege" in str(exc)
    else:
        raise AssertionError("invalid head truth privilege was accepted")
