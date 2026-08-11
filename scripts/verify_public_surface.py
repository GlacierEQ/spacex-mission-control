from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOKEN = "LOCAL_MISSION_OPS_SIMULATION_NOT_FLIGHT_COMMAND_AUTHORITY"


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def main() -> None:
    readme = read("README.md")
    orchestrator = read("src/omega/mission_orchestrator.py")
    console = read("src/console.py")
    capabilities = json.loads(read("machine/capabilities.json"))
    target = json.loads(read("machine/target-contract.json"))

    assert TOKEN in readme
    assert TOKEN in orchestrator
    assert target["evidence_token"] == TOKEN
    assert "not affiliated with, endorsed by" in readme
    assert "create_demo_mission" in orchestrator
    assert "Backward-compatible historical alias" in orchestrator
    assert "class Bus" in console
    assert "Unified Flight Operations Center" not in readme
    assert "sub-second telemetry rendering" not in readme
    assert "1000+ telemetry parameters" not in readme
    assert "Fully wired into APEX Highway mesh" not in readme
    assert "hyper-scaling" not in capabilities["capabilities"]
    assert target["current"]["deployed"] is False

    print(TOKEN)


if __name__ == "__main__":
    main()
