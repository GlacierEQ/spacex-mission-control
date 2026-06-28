"""Mission orchestrator — coordinates all subsystems during flight phases.

State machine for mission timeline: pre-launch, ascent, staging, coast,
entry, landing. Triggers subsystem actions at phase transitions.
"""

import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Callable, Optional

from alpha.telemetry_aggregator import TelemetryAggregator, TelemetryPoint, SourceType


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
        if self._phase_start == 0:
            return 0.0
        return time.time() - self._phase_start

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

        old_phase = self._phase
        self._phase = new_phase
        self._phase_start = time.time()

        entry = MissionEvent(
            time=time.time(),
            phase=new_phase,
            event=f"{old_phase.name} -> {new_phase.name}: {event}",
        )
        self._event_log.append(entry)

        for cb in self._callbacks.get(new_phase, []):
            cb({"phase": new_phase, "from": old_phase})

        for cb in self._global_callbacks:
            cb({"phase": new_phase, "from": old_phase})

        self._execute_actions(new_phase)

        return True

    def _execute_actions(self, phase: MissionPhase):
        for action in self._actions:
            if action.phase == phase and not action.executed:
                try:
                    action.action()
                    action.executed = True
                except Exception as e:
                    self._event_log.append(MissionEvent(
                        time=time.time(), phase=phase,
                        event=f"action_failed: {action.subsystem}: {e}",
                    ))

    def check_transitions(self) -> Optional[MissionPhase]:
        if self._phase in (MissionPhase.ABORT, MissionPhase.MISSION_COMPLETE):
            return None

        for t in self._transitions:
            if t.from_phase == self._phase:
                try:
                    if t.condition():
                        self.transition_to(t.to_phase, t.name)
                        return t.to_phase
                except Exception:
                    pass
        return None

    def abort(self, reason: str = "manual") -> bool:
        if self._phase in (MissionPhase.ABORT, MissionPhase.MISSION_COMPLETE):
            return False

        self._abort_reason = reason
        self._phase = MissionPhase.ABORT
        self._phase_start = time.time()

        entry = MissionEvent(
            time=time.time(), phase=MissionPhase.ABORT,
            event=f"ABORT: {reason}",
        )
        self._event_log.append(entry)

        for cb in self._callbacks.get(MissionPhase.ABORT, []):
            cb({"phase": MissionPhase.ABORT, "reason": reason})

        return True

    def ingest_telemetry(self, point: TelemetryPoint):
        self.aggregator.ingest(point)

    @property
    def event_log(self) -> list[dict]:
        return [
            {"time": e.time, "phase": e.phase.name, "event": e.event}
            for e in self._event_log
        ]

    @property
    def mission_summary(self) -> dict:
        return {
            "current_phase": self._phase.name,
            "phase_elapsed": round(self.phase_elapsed, 1),
            "events": len(self._event_log),
            "telemetry_points": len(self.aggregator._buffer),
            "abort_reason": self._abort_reason or None,
        }


def create_f9_mission(orchestrator: MissionOrchestrator):
    """Configure Falcon 9 mission profile transitions."""
    from alpha.telemetry_aggregator import TelemetryPoint

    def check_liftoff():
        p = orchestrator.aggregator.get_metric("altitude")
        return p and p.latest > 10

    def check_meco():
        p = orchestrator.aggregator.get_metric("altitude")
        return p and p.latest > 60000

    def check_staging():
        m = orchestrator.aggregator.get_metric("meco_complete")
        return m and m.latest > 0

    def check_orbit():
        v = orchestrator.aggregator.get_metric("velocity")
        return v and v.latest > 7800

    transitions = [
        PhaseTransition(MissionPhase.PRE_LAUNCH, MissionPhase.COUNTDOWN, lambda: True, "auto"),
        PhaseTransition(MissionPhase.COUNTDOWN, MissionPhase.LIFTOFF, check_liftoff, "altitude > 10m"),
        PhaseTransition(MissionPhase.LIFTOFF, MissionPhase.ASCENT, lambda: True, "auto"),
        PhaseTransition(MissionPhase.ASCENT, MissionPhase.MECO, check_meco, "altitude > 60km"),
        PhaseTransition(MissionPhase.MECO, MissionPhase.STAGE_SEPARATION, check_staging, "meco_confirmed"),
        PhaseTransition(MissionPhase.STAGE_SEPARATION, MissionPhase.SECOND_ENGINE_START, lambda: True, "auto"),
        PhaseTransition(MissionPhase.STAGE_SEPARATION, MissionPhase.FIRST_STAGE_BURNBACK, lambda: True, "auto"),
        PhaseTransition(MissionPhase.SECOND_ENGINE_START, MissionPhase.FAIRING_SEPARATION, lambda: True, "auto"),
        PhaseTransition(MissionPhase.SECOND_ENGINE_START, MissionPhase.SECOND_STAGE_BURN, lambda: True, "auto"),
        PhaseTransition(MissionPhase.SECOND_STAGE_BURN, MissionPhase.COAST, check_orbit, "orbit_reached"),
        PhaseTransition(MissionPhase.COAST, MissionPhase.ORBITAL_INSERTION, lambda: True, "auto"),
        PhaseTransition(MissionPhase.ORBITAL_INSERTION, MissionPhase.DEPLOY, lambda: True, "auto"),
        PhaseTransition(MissionPhase.DEPLOY, MissionPhase.MISSION_COMPLETE, lambda: True, "auto"),
    ]

    for t in transitions:
        orchestrator.add_transition(t)
