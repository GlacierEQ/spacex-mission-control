# SpaceX Mission Control

Mission operations dashboard and orchestrator for Falcon 9 / Starship flights.

## Architecture

**Double Helix (Alpha + Omega)**

- **Alpha** (`src/alpha/telemetry_aggregator.py`): Unified telemetry merge — time sync, metric aggregation, rate conversion, EMA smoothing.
- **Omega** (`src/omega/mission_orchestrator.py`): Flight phase state machine — transitions, subsystem actions, event logging.

## Features

- Multi-source telemetry aggregation with time synchronization
- Metric types: counter, gauge, rate, histogram
- Derivative and EMA computation
- 17-phase Falcon 9 mission profile
- Automated phase transitions with conditions
- Subsystem action triggers
- Event logging and dashboard summary
- Zero external dependencies
