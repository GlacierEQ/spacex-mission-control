"""Recovery proof for expiring local command-intent authority."""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from omega.command_authority import CommandAuthorityHalfLife
from omega.mission_orchestrator import MissionOrchestrator, MissionPhase, SubsystemAction


class Clock:
    def __init__(self, now: float = 1_000.0) -> None:
        self.now = now

    def __call__(self) -> float:
        return self.now


def authority(clock: Clock) -> CommandAuthorityHalfLife:
    return CommandAuthorityHalfLife(b"a" * 32, clock=clock, max_ttl_seconds=60)


def test_signed_authority_executes_controlled_action_once() -> None:
    clock = Clock()
    plane = authority(clock)
    orch = MissionOrchestrator(authority_plane=plane)
    executed: list[str] = []
    action = SubsystemAction(
        MissionPhase.LIFTOFF,
        "demo-engine",
        lambda: executed.append("fired"),
        requires_authority=True,
        authority_scope="demo:engine:enable",
    )
    orch.add_action(action)
    orch.authorize_action(action, subject="flight-director-sim", ttl_seconds=15)

    assert orch.transition_to(MissionPhase.LIFTOFF)
    assert executed == ["fired"]
    assert action.executed is True
    assert plane.consumed_count == 1
    receipt = orch.event_log[-1]["details"]["authority"]
    assert receipt["authorized"] is True
    assert receipt["scope"] == "demo:engine:enable"


def test_expired_authority_blocks_action_without_consuming_it() -> None:
    clock = Clock()
    plane = authority(clock)
    orch = MissionOrchestrator(authority_plane=plane)
    executed: list[str] = []
    action = SubsystemAction(
        MissionPhase.LIFTOFF,
        "demo-engine",
        lambda: executed.append("fired"),
        requires_authority=True,
    )
    orch.add_action(action)
    orch.authorize_action(action, subject="operator-sim", ttl_seconds=5)
    clock.now += 6

    orch.transition_to(MissionPhase.LIFTOFF)
    assert executed == []
    assert action.executed is False
    assert plane.consumed_count == 0
    assert orch.event_log[-1]["event"] == "action_blocked: demo-engine"
    assert orch.event_log[-1]["details"]["authority"]["reason"] == "token_expired"


def test_scope_mismatch_fails_closed() -> None:
    clock = Clock()
    plane = authority(clock)
    token = plane.issue(subject="operator-sim", scope="demo:a", ttl_seconds=10)
    receipt = plane.consume(token, required_scope="demo:b", required_subject="operator-sim")
    assert receipt.authorized is False
    assert receipt.reason == "scope_mismatch"
    assert plane.consumed_count == 0


def test_consumed_token_cannot_be_replayed() -> None:
    clock = Clock()
    plane = authority(clock)
    token = plane.issue(subject="operator-sim", scope="demo:a", ttl_seconds=10)

    first = plane.consume(token, required_scope="demo:a", required_subject="operator-sim")
    second = plane.consume(token, required_scope="demo:a", required_subject="operator-sim")

    assert first.authorized is True
    assert second.authorized is False
    assert second.reason == "token_already_consumed"
    assert plane.consumed_count == 1


def test_controlled_action_without_authority_plane_is_blocked() -> None:
    orch = MissionOrchestrator()
    executed: list[str] = []
    action = SubsystemAction(
        MissionPhase.LIFTOFF,
        "demo-engine",
        lambda: executed.append("fired"),
        requires_authority=True,
    )
    orch.add_action(action)

    orch.transition_to(MissionPhase.LIFTOFF)
    assert executed == []
    assert action.executed is False
    assert orch.event_log[-1]["details"]["reason"] == "authority_plane_not_configured"


def test_uncontrolled_legacy_simulation_action_remains_compatible() -> None:
    orch = MissionOrchestrator()
    executed: list[str] = []
    orch.add_action(
        SubsystemAction(MissionPhase.LIFTOFF, "legacy-demo", lambda: executed.append("ran"))
    )

    orch.transition_to(MissionPhase.LIFTOFF)
    assert executed == ["ran"]
