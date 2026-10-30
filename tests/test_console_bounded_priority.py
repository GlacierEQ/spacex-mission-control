"""Real regressions for bounded, priority-preserving mission-console fan-out."""
from concurrent.futures import ThreadPoolExecutor
import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from console import Bus, Console, Event


def test_priority_overflow_preserves_critical_event():
    bus = Bus()
    fd = Console("FD", max_pending=2)
    bus.register(fd)
    bus.publish(Event("engine", 5, "critical"))
    bus.publish(Event("operator", 4, "important"))
    r = bus.publish(Event("display", 1, "noncritical"))
    assert r["rejected_overflow"] == ["FD"]
    assert r["delivered"] == []
    assert [x.msg for x in fd.inbox] == ["critical", "important"]
    assert bus.stats()["consoles"]["FD"]["dropped_overflow"] == 1


def test_urgent_message_displaces_oldest_lowest_priority():
    bus = Bus()
    fd = Console("FD", max_pending=2)
    bus.register(fd)
    bus.publish(Event("a", 2, "oldest weak"))
    bus.publish(Event("b", 3, "more important"))
    r = bus.publish(Event("c", 5, "critical"))
    assert r["delivered"] == ["FD"]
    assert r["overflowed"] == ["FD"]
    assert [x.msg for x in bus.drain("FD")] == ["more important", "critical"]
    assert bus.stats()["dropped_overflow"] == 1


def test_drain_releases_capacity_without_resetting_drop_audit():
    bus = Bus()
    bus.register(Console("FD", max_pending=1))
    bus.publish(Event("a", 1, "first"))
    bus.publish(Event("b", 1, "second"))
    assert bus.stats()["consoles"]["FD"]["pending"] == 1
    assert [x.msg for x in bus.drain("FD")] == ["second"]
    bus.publish(Event("c", 2, "third"))
    assert [x.msg for x in bus.drain("FD")] == ["third"]
    assert bus.stats()["dropped_overflow"] == 1
    assert bus.stats()["published"] == 3


def test_duplicate_console_name_never_discards_queued_events():
    bus = Bus()
    old = Console("FD")
    bus.register(old)
    bus.publish(Event("a", 3, "queued"))
    bus.register(old)
    with pytest.raises(ValueError, match="duplicate"):
        bus.register(Console("FD"))
    assert [x.msg for x in bus.drain("FD")] == ["queued"]


@pytest.mark.parametrize("severity", [False, True, 1.5, 0, 6])
def test_invalid_event_severity_rejected(severity):
    with pytest.raises(ValueError):
        Event("source", severity, "message")


@pytest.mark.parametrize("limit", [False, 0, -1, 1.5])
def test_invalid_console_capacity_rejected(limit):
    with pytest.raises(ValueError):
        Console("x", max_pending=limit)


def test_concurrent_publish_and_delivery_has_no_missing_events():
    bus = Bus()
    bus.register(Console("all", max_pending=1000))
    events = [Event("s", 3, str(i)) for i in range(300)]
    with ThreadPoolExecutor(max_workers=24) as pool:
        outcomes = list(pool.map(bus.publish, events))
    received = bus.drain("all")
    assert all(x["delivered"] == ["all"] for x in outcomes)
    assert len(received) == 300
    assert {x.msg for x in received} == {str(i) for i in range(300)}
    assert bus.stats()["published"] == 300
    assert bus.stats()["dropped_overflow"] == 0


def test_minimum_severity_filtering_is_not_counted_as_overflow():
    bus = Bus()
    bus.register(Console("critical", min_sev=5, max_pending=1))
    r = bus.publish(Event("operator", 3, "ordinary"))
    assert r["delivered"] == []
    assert r["undelivered"] == ["critical"]
    assert r["overflowed"] == []
    assert bus.stats()["dropped_overflow"] == 0
