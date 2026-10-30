#!/usr/bin/env python3
"""Bounded concurrent synthetic mission-console event fan-out.

This is a local simulation component, not flight-command authority.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from threading import RLock


@dataclass(frozen=True)
class Event:
    source: str
    severity: int
    msg: str

    def __post_init__(self) -> None:
        if isinstance(self.severity, bool) or not isinstance(self.severity, int) or not (1 <= self.severity <= 5):
            raise ValueError("severity must be an integer in 1..5")
        if not isinstance(self.source, str) or not self.source.strip():
            raise ValueError("event source required")
        if not isinstance(self.msg, str):
            raise ValueError("event message must be text")


@dataclass
class Console:
    name: str
    min_sev: int = 1
    inbox: list[Event] = field(default_factory=list)
    max_pending: int = 10_000
    dropped_overflow: int = 0

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("console name required")
        if isinstance(self.min_sev, bool) or not isinstance(self.min_sev, int) or not (1 <= self.min_sev <= 5):
            raise ValueError("min_sev must be an integer in 1..5")
        if isinstance(self.max_pending, bool) or not isinstance(self.max_pending, int) or self.max_pending < 1:
            raise ValueError("max_pending must be a positive integer")
        if len(self.inbox) > self.max_pending:
            raise ValueError("initial inbox exceeds max_pending")


class Bus:
    """Bounded, priority-retaining fan-out with explicit overflow receipts.

    One lock protects register/publish/drain and prevents lost updates.
    On full queues, higher-severity events displace the oldest lowest-severity
    queued event; less severe events are dropped without losing an urgent hold.
    """

    def __init__(self) -> None:
        self.consoles: dict[str, Console] = {}
        self.published = 0
        self.dropped_overflow = 0
        self._lock = RLock()

    def register(self, c: Console) -> None:
        if not isinstance(c, Console):
            raise TypeError("register requires a Console")
        with self._lock:
            existing = self.consoles.get(c.name)
            if existing is not None and existing is not c:
                raise ValueError("duplicate console name would overwrite queued events")
            self.consoles[c.name] = c

    def publish(self, e: Event) -> dict:
        if not isinstance(e, Event):
            raise TypeError("publish requires an Event")
        delivered: list[str] = []
        overflowed: list[str] = []
        rejected: list[str] = []
        with self._lock:
            for c in self.consoles.values():
                if e.severity < c.min_sev:
                    continue
                if len(c.inbox) >= c.max_pending:
                    weakest = min(x.severity for x in c.inbox)
                    self.dropped_overflow += 1
                    c.dropped_overflow += 1
                    overflowed.append(c.name)
                    if e.severity < weakest:
                        rejected.append(c.name)
                        continue
                    # Evict the oldest weakest event; preserve more severe ones.
                    oldest_weakest = next(i for i, old in enumerate(c.inbox) if old.severity == weakest)
                    del c.inbox[oldest_weakest]
                c.inbox.append(e)
                delivered.append(c.name)
            self.published += 1
            return {
                "delivered": sorted(delivered),
                "severity": e.severity,
                "source": e.source,
                "undelivered": sorted(set(self.consoles) - set(delivered)),
                "overflowed": sorted(overflowed),
                "rejected_overflow": sorted(rejected),
            }

    def drain(self, console_name: str) -> list[Event]:
        with self._lock:
            c = self.consoles.get(console_name)
            if c is None:
                return []
            out = list(c.inbox)
            c.inbox.clear()
            return out

    def stats(self) -> dict:
        with self._lock:
            return {
                "published": self.published,
                "dropped_overflow": self.dropped_overflow,
                "consoles": {
                    name: {
                        "pending": len(c.inbox),
                        "max_pending": c.max_pending,
                        "dropped_overflow": c.dropped_overflow,
                        "min_severity": c.min_sev,
                    } for name, c in sorted(self.consoles.items())
                },
            }


if __name__ == "__main__":
    bus = Bus()
    bus.register(Console("FD", 3, max_pending=2))
    bus.register(Console("Prop", 2))
    print(bus.publish(Event("tanks", 4, "pressure high")))
    print([e.msg for e in bus.drain("FD")])
