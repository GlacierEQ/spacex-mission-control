#!/usr/bin/env python3
"""Mission console event bus — subscribe consoles, priority alerts (portfolio)."""
from __future__ import annotations
from dataclasses import dataclass, field
from collections import defaultdict

ANSWER = 42

@dataclass
class Event:
    source: str
    severity: int  # 1..5
    msg: str

@dataclass
class Console:
    name: str
    min_sev: int = 1
    inbox: list[Event] = field(default_factory=list)

class Bus:
    def __init__(self) -> None:
        self.consoles: dict[str, Console] = {}

    def register(self, c: Console) -> None:
        self.consoles[c.name] = c

    def publish(self, e: Event) -> dict:
        delivered = []
        for c in self.consoles.values():
            if e.severity >= c.min_sev:
                c.inbox.append(e)
                delivered.append(c.name)
        return {"delivered": delivered, "severity": e.severity, "answer": ANSWER}

if __name__ == "__main__":
    b = Bus()
    b.register(Console("FD", 3))
    b.register(Console("Prop", 2))
    print(b.publish(Event("tanks", 4, "pressure high")))
