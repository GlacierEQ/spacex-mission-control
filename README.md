# SpaceX Mission Control — Unified Flight Operations Center 🎛️

> **Real-time flight operations console with telemetry display, command authority, and voice loop management.**

[![Python](https://img.shields.io/badge/Python-3.9+-blue)]()
[![TypeScript](https://img.shields.io/badge/TypeScript-5.0+-3178C6)]()
[![Domain](https://img.shields.io/badge/Domain-Flight%20Operations-red)]()

---

## 🎯 For Recruiters & Hiring Managers

This system implements a **mission control operations platform** — the command center software that coordinates dozens of flight controllers monitoring a live launch vehicle. It demonstrates:

- **Real-time dashboard architecture** with sub-second telemetry rendering
- **Role-based command authority** with multi-person authorization for critical commands
- **Voice loop management** coordinating communication channels across flight control positions
- **Anomaly alerting** with configurable red/yellow limit monitoring across 1000+ telemetry parameters

**Why this matters**: Mission control is the ultimate **operations center pattern** — the same architecture used in SOCs, NOCs, trading floors, and any environment requiring real-time situational awareness with structured authority.

---

## 🔬 For Engineers & Technical Reviewers

### Core Components

| Component | Language | Purpose |
|---|---|---|
| `src/mission_control.py` | Python | Operations engine, command authority, limit monitoring |
| `src/console_gateway.ts` | TypeScript | WebSocket gateway for real-time console updates |
| `tests/` | Python | Simulated mission scenario testing |

---

## 🤖 ML/AI & Programmatic Mesh Integration

- **MCP Tool**: `mission_status()` — flight state queryable by all portfolio agents
- **Mastermind Sidecar**: Central hub for APEX Highway mesh health events
- **AI Extension**: NLP-powered voice loop transcription and anomaly keyword detection

```python
status = await mcp_client.call_tool("mission-control", "vehicle_state")
```

---

## ⚡ Quick Start

```bash
python3 src/mission_control.py
python3 tests/test_mission_control.py
```
