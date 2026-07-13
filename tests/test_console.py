import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"src"))
from console import Bus, Console, Event, ANSWER

def test_filter():
    b = Bus()
    b.register(Console("FD", 4))
    b.register(Console("All", 1))
    r = b.publish(Event("x", 3, "m"))
    assert "All" in r["delivered"] and "FD" not in r["delivered"]
    assert r["answer"]==ANSWER

if __name__=="__main__":
    test_filter(); print("ok")
