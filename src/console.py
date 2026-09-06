#!/usr/bin/env python3
"""Mission console event bus — priority-filtered multi-console delivery.

Human-readable ops surface for flight director style fan-out.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Event:
    source: str
    severity: int  # 1 (info) .. 5 (abort-class)
    msg: str

    def __post_init__(self) -> None:
        if not 1 <= self.severity <= 5:
            raise ValueError("severity must be in 1..5")


@dataclass
class Console:
    name: str
    min_sev: int = 1
    inbox: list[Event] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not 1 <= self.min_sev <= 5:
            raise ValueError("min_sev must be in 1..5")


class Bus:
    """Publish events to consoles that match severity thresholds."""

    def __init__(self) -> None:
        self.consoles: dict[str, Console] = {}
        self.published = 0

    def register(self, c: Console) -> None:
        if not c.name:
            raise ValueError("console name required")
        self.consoles[c.name] = c

    def publish(self, e: Event) -> dict:
        delivered: list[str] = []
        for c in self.consoles.values():
            if e.severity >= c.min_sev:
                c.inbox.append(e)
                delivered.append(c.name)
        self.published += 1
        return {
            "delivered": sorted(delivered),
            "severity": e.severity,
            "source": e.source,
            "undelivered": sorted(set(self.consoles) - set(delivered)),
        }

    def drain(self, console_name: str) -> list[Event]:
        c = self.consoles.get(console_name)
        if not c:
            return []
        out = list(c.inbox)
        c.inbox.clear()
        return out


if __name__ == "__main__":
    b = Bus()
    b.register(Console("FD", 3))
    b.register(Console("Prop", 2))
    print(b.publish(Event("tanks", 4, "pressure high")))
    print([e.msg for e in b.drain("FD")])
