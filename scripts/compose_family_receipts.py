#!/usr/bin/env python3
"""Compose verified specialist receipts through the FAM-SPACEX routing head."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ROUTING_PATH = ROOT / "machine" / "family-routing.json"
COMPOSITION_SCHEMA = "glaciereq.apex-family-composition-receipt.v1"


def _stable(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _digest(value: object) -> str:
    return hashlib.sha256(_stable(value)).hexdigest()


def _validate_routing_invariants(routing: dict[str, Any]) -> None:
    if routing.get("schema") != "glaciereq.apex-family-routing.v1":
        raise ValueError("unsupported family-routing schema")
    if routing.get("head_role") != "ROUTING_COMPOSITION_MASTER":
        raise ValueError("family head must remain ROUTING_COMPOSITION_MASTER")
    if routing.get("routing_privilege") != "ROUTING_COMPOSITION_ONLY":
        raise ValueError("family head routing privilege must remain routing/composition only")
    if routing.get("capability_truth_privilege") is not False:
        raise ValueError("family head routing role may not create capability truth privilege")
    if routing.get("head_implementation_revisable") is not True:
        raise ValueError("family head implementation must remain revisable")


def load_routing(path: Path = ROUTING_PATH) -> dict[str, Any]:
    routing = json.loads(path.read_text(encoding="utf-8"))
    _validate_routing_invariants(routing)
    return routing


def member_index(routing: dict[str, Any]) -> dict[str, dict[str, Any]]:
    _validate_routing_invariants(routing)
    return {row["receipt_schema"]: row for row in routing.get("members", [])}


def verify_member_receipt(receipt: dict[str, Any], routing: dict[str, Any]) -> dict[str, Any]:
    _validate_routing_invariants(routing)
    schema = receipt.get("schema")
    member = member_index(routing).get(schema)
    if member is None:
        raise ValueError(f"unregistered specialist receipt schema: {schema!r}")
    if receipt.get("selection_mode") != "CURRENT_BEST_REVISABLE":
        raise ValueError(f"{member['repository']} receipt selection is not revisable")
    supplied = receipt.get("receipt_sha256")
    if not isinstance(supplied, str) or len(supplied) != 64:
        raise ValueError(f"{member['repository']} receipt has no valid SHA-256 identity")
    body = dict(receipt)
    body.pop("receipt_sha256", None)
    calculated = _digest(body)
    if calculated != supplied:
        raise ValueError(f"{member['repository']} receipt hash mismatch")
    if receipt.get("external_actions_executed", 0) != 0:
        raise ValueError(f"{member['repository']} receipt reports unexpected external actions")

    capabilities = receipt.get("capabilities")
    if not isinstance(capabilities, list):
        capability = receipt.get("capability")
        capabilities = [capability] if isinstance(capability, str) and capability else []
    expected = set(member.get("capabilities", []))
    observed = set(capabilities)
    if expected and not expected.intersection(observed):
        raise ValueError(f"{member['repository']} receipt does not expose an expected capability")

    return {
        "repository": member["repository"],
        "role": member["role"],
        "receipt_schema": schema,
        "receipt_sha256": supplied,
        "capabilities": capabilities,
        "evidence_state": receipt.get("evidence_state"),
    }


def build_plan(routing: dict[str, Any]) -> dict[str, Any]:
    _validate_routing_invariants(routing)
    members = [
        {
            "repository": row["repository"],
            "role": row["role"],
            "capabilities": row["capabilities"],
            "operator_surface": row["operator_surface"],
            "receipt_schema": row["receipt_schema"],
        }
        for row in routing.get("members", [])
    ]
    body = {
        "schema": "glaciereq.apex-family-routing-plan.v1",
        "family_id": routing["family_id"],
        "head_repository": routing["head_repository"],
        "selection_mode": routing["selection_mode"],
        "members": members,
        "parallelizable": True,
        "compose_at": routing["composition_surface"],
    }
    return {**body, "plan_sha256": _digest(body)}


def compose(receipts: list[dict[str, Any]], routing: dict[str, Any]) -> dict[str, Any]:
    _validate_routing_invariants(routing)
    verified = [verify_member_receipt(receipt, routing) for receipt in receipts]
    repositories = [row["repository"] for row in verified]
    if len(repositories) != len(set(repositories)):
        raise ValueError("duplicate specialist receipt in one composition")
    capabilities = sorted({cap for row in verified for cap in row["capabilities"]})
    body = {
        "schema": COMPOSITION_SCHEMA,
        "family_id": routing["family_id"],
        "head_repository": routing["head_repository"],
        "head_role": routing["head_role"],
        "selection_mode": routing["selection_mode"],
        "routing_privilege": routing["routing_privilege"],
        "capability_truth_privilege": False,
        "member_receipts": sorted(verified, key=lambda row: row["repository"]),
        "composed_capabilities": capabilities,
        "member_count": len(verified),
        "status": "PASS",
    }
    return {**body, "receipt_sha256": _digest(body)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("receipts", nargs="*", type=Path)
    parser.add_argument("--plan", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    routing = load_routing()
    if args.plan:
        result = build_plan(routing)
    else:
        if not args.receipts:
            parser.error("provide specialist receipt files or use --plan")
        result = compose(
            [json.loads(path.read_text(encoding="utf-8")) for path in args.receipts],
            routing,
        )
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
