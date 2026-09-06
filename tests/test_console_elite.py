"""Elite tests for mission console bus."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from console import Bus, Console, Event


def test_severity_fanout():
    b = Bus()
    b.register(Console("FD", 3))
    b.register(Console("Prop", 2))
    b.register(Console("PR", 5))
    r = b.publish(Event("tanks", 4, "pressure high"))
    assert "FD" in r["delivered"]
    assert "Prop" in r["delivered"]
    assert "PR" not in r["delivered"]
    assert "PR" in r["undelivered"]


def test_drain():
    b = Bus()
    b.register(Console("FD", 1))
    b.publish(Event("gnc", 2, "hold"))
    msgs = b.drain("FD")
    assert len(msgs) == 1
    assert msgs[0].msg == "hold"
    assert b.drain("FD") == []


def test_bad_severity():
    try:
        Event("x", 9, "nope")
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_no_magic_answer():
    b = Bus()
    b.register(Console("FD", 1))
    r = b.publish(Event("a", 1, "hi"))
    assert "answer" not in r
