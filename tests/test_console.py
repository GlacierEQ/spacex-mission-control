"""Mission console tests (elite — no ANSWER theater)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from console import Bus, Console, Event


def test_publish_filters():
    b = Bus()
    b.register(Console("FD", 3))
    b.register(Console("Prop", 2))
    r = b.publish(Event("tanks", 4, "pressure high"))
    assert "FD" in r["delivered"]
    assert "Prop" in r["delivered"]


def test_low_sev_only_prop():
    b = Bus()
    b.register(Console("FD", 3))
    b.register(Console("Prop", 2))
    r = b.publish(Event("gnc", 2, "note"))
    assert r["delivered"] == ["Prop"]
