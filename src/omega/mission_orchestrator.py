"""Repository-local mission-operations state-machine laboratory.

The phases and threshold transitions are synthetic portfolio fixtures for testing
orchestration, callbacks, event history, abort behavior, and telemetry-driven
state transitions. They are not SpaceX procedures, Falcon/Starship flight rules,
mission data, or command authority.
"""

import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Callable, Optional

from alpha.telemetry_aggregator import TelemetryAggregator, TelemetryPoint

EVIDENCE_STATE = "LOCAL_MISSION_OPS_SIMULATION_NOT_FLIGHT_COMMAND_AUTHORITY"


class MissionPhase(Enum):
    PRE_LAUNCH = auto()
    COUNTDOWN = auto()
    LIFTOFF = auto()
    ASCENT = auto()
    MECO = auto()
    STAGE_SEPARATION = auto()
    SECOND_ENGINE_START = auto()
    FIRST_STAGE_BURNBACK = auto()
    FIRST_STAGE_ENTRY = auto()
    FIRST_STAGE_LANDING = auto()
    SECOND_STAGE_BURN = auto()
    FAIRING_SEPARATION = auto()
    COAST = auto()
    ORBITAL_INSERTION = auto()
    DEPLOY = auto()
    MISSION_COMPLETE = auto()
    ABORT = auto()


@dataclass
class PhaseTransition:
    from_phase: MissionPhase
    to_phase: MissionPhase
    condition: Callable[[], bool]
    name: str = ""


@dataclass
class MissionEvent:
    time: float
    phase: MissionPhase
    event: str
    details: dict = field(default_factory=dict)


@dataclass
class SubsystemAction:
    phase: MissionPhase
    subsystem: str
    action: Callable
    executed: bool = False


class MissionOrchestrator:
    def __init__(self, aggregator: Optional[TelemetryAggregator] = None):
        self.aggregator = aggregator or TelemetryAggregator()
        self._phase = MissionPhase.PRE_LAUNCH
        self._transitions: list[PhaseTransition] = []
        self._actions: list[SubsystemAction] = []
        self._event_log: list[MissionEvent] = []
        self._phase_start: float = 0.0
        self._mission_start: float = 0.0
        self._callbacks: dict[MissionPhase, list[Callable]] = {}
        self._global_callbacks: list[Callable] = []
        self._abort_reason: str = ""

    @property
    def phase(self) -> MissionPhase:
        return self._phase

    @property
    def phase_elapsed(self) -> float:
        if self._phase_start == 0:
            return 0.0
        return time.time() - self._phase_start

    @property
    def mission_elapsed(self) -> float:
        if self._mission_start == 0:
            return 0.0
        return time.time() - self._mission_start

    def add_transition(self, transition: PhaseTransition):
        self._transitions.append(transition)

    def add_action(self, action: SubsystemAction):
        self._actions.append(action)

    def on_phase(self, phase: MissionPhase, callback: Callable):
        self._callbacks.setdefault(phase, []).append(callback)

    def on_any_phase(self, callback: Callable):
        self._global_callbacks.append(callback)

    def transition_to(self, new_phase: MissionPhase, event: str = "manual") -> bool:
        if self._phase == MissionPhase.ABORT:
            return False

        now = time.time()
        old_phase = self._phase
        if self._mission_start == 0:
            self._mission_start = now
        self._phase = new_phase
        self._phase_start = now

        entry = MissionEvent(
            time=now,
            phase=new_phase,
            event=f"{old_phase.name} -> {new_phase.name}: {event}",
            details={"evidence_state": EVIDENCE_STATE},
        )
        self._event_log.append(entry)

        for callback in self._callbacks.get(new_phase, []):
            callback({"phase": new_phase, "from": old_phase})

        for callback in self._global_callbacks:
            callback({"phase": new_phase, "from": old_phase})

        self._execute_actions(new_phase)
        return True

    def _execute_actions(self, phase: MissionPhase):
        for action in self._actions:
            if action.phase == phase and not action.executed:
                try:
                    action.action()
                    action.executed = True
                except Exception:
                    self._event_log.append(
                        MissionEvent(
                            time=time.time(),
                            phase=phase,
                            event=f"action_failed: {action.subsystem}",
                            details={"evidence_state": EVIDENCE_STATE},
                        )
                    )

    def check_transitions(self) -> Optional[MissionPhase]:
        if self._phase in (MissionPhase.ABORT, MissionPhase.MISSION_COMPLETE):
            return None

        for transition in self._transitions:
            if transition.from_phase != self._phase:
                continue
            try:
                ready = transition.condition()
            except Exception:
                ready = False
            if ready:
                self.transition_to(transition.to_phase, transition.name)
                return transition.to_phase
        return None

    def abort(self, reason: str = "manual") -> bool:
        if self._phase in (MissionPhase.ABORT, MissionPhase.MISSION_COMPLETE):
            return False

        now = time.time()
        if self._mission_start == 0:
            self._mission_start = now
        self._abort_reason = reason
        self._phase = MissionPhase.ABORT
        self._phase_start = now
        self._event_log.append(
            MissionEvent(
                time=now,
                phase=MissionPhase.ABORT,
                event=f"ABORT: {reason}",
                details={"evidence_state": EVIDENCE_STATE},
            )
        )

        for callback in self._callbacks.get(MissionPhase.ABORT, []):
            callback({"phase": MissionPhase.ABORT, "reason": reason})
        return True

    def ingest_telemetry(self, point: TelemetryPoint):
        self.aggregator.ingest(point)

    @property
    def event_log(self) -> list[dict]:
        return [
            {
                "time": event.time,
                "phase": event.phase.name,
                "event": event.event,
                "evidence_state": EVIDENCE_STATE,
            }
            for event in self._event_log
        ]

    @property
    def mission_summary(self) -> dict:
        return {
            "current_phase": self._phase.name,
            "phase_elapsed": round(self.phase_elapsed, 1),
            "mission_elapsed": round(self.mission_elapsed, 1),
            "events": len(self._event_log),
            "telemetry_points": len(self.aggregator._buffer),
            "abort_reason": self._abort_reason or None,
            "evidence_state": EVIDENCE_STATE,
        }


def create_demo_mission(orchestrator: MissionOrchestrator):
    """Configure synthetic two-stage mission transitions for local tests only."""

    def check_liftoff():
        point = orchestrator.aggregator.get_metric("altitude")
        return bool(point and point.latest > 10)

    def check_meco():
        point = orchestrator.aggregator.get_metric("altitude")
        return bool(point and point.latest > 60000)

    def check_staging():
        point = orchestrator.aggregator.get_metric("meco_complete")
        return bool(point and point.latest > 0)

    def check_orbit():
        point = orchestrator.aggregator.get_metric("velocity")
        return bool(point and point.latest > 7800)

    transitions = [
        PhaseTransition(MissionPhase.PRE_LAUNCH, MissionPhase.COUNTDOWN, lambda: True, "auto"),
        PhaseTransition(MissionPhase.COUNTDOWN, MissionPhase.LIFTOFF, check_liftoff, "demo altitude gate"),
        PhaseTransition(MissionPhase.LIFTOFF, MissionPhase.ASCENT, lambda: True, "auto"),
        PhaseTransition(MissionPhase.ASCENT, MissionPhase.MECO, check_meco, "demo altitude gate"),
        PhaseTransition(MissionPhase.MECO, MissionPhase.STAGE_SEPARATION, check_staging, "demo stage gate"),
        PhaseTransition(MissionPhase.STAGE_SEPARATION, MissionPhase.SECOND_ENGINE_START, lambda: True, "auto"),
        PhaseTransition(MissionPhase.STAGE_SEPARATION, MissionPhase.FIRST_STAGE_BURNBACK, lambda: True, "auto"),
        PhaseTransition(MissionPhase.SECOND_ENGINE_START, MissionPhase.FAIRING_SEPARATION, lambda: True, "auto"),
        PhaseTransition(MissionPhase.SECOND_ENGINE_START, MissionPhase.SECOND_STAGE_BURN, lambda: True, "auto"),
        PhaseTransition(MissionPhase.SECOND_STAGE_BURN, MissionPhase.COAST, check_orbit, "demo velocity gate"),
        PhaseTransition(MissionPhase.COAST, MissionPhase.ORBITAL_INSERTION, lambda: True, "auto"),
        PhaseTransition(MissionPhase.ORBITAL_INSERTION, MissionPhase.DEPLOY, lambda: True, "auto"),
        PhaseTransition(MissionPhase.DEPLOY, MissionPhase.MISSION_COMPLETE, lambda: True, "auto"),
    ]

    for transition in transitions:
        orchestrator.add_transition(transition)


def create_f9_mission(orchestrator: MissionOrchestrator):
    """Backward-compatible historical alias for the synthetic demo profile.

    The name does not imply Falcon 9 compatibility, SpaceX procedure knowledge,
    or flight authority. New code should call :func:`create_demo_mission`.
    """

    create_demo_mission(orchestrator)
