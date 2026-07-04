# HELIX Architecture — spacex-mission-control

## Double Helix Pattern

**Alpha (What)** — Pure physics models, stateless computation
- telemetry_aggregator

**Omega (How)** — Controllers, orchestration, stateful management  
- cross_domain_fusion,mission_orchestrator

## Design Principles

- Zero external dependencies (stdlib only)
- Stateless alpha, stateful omega
- SHA-256 file integrity verification
- Shadow watchdog daemon monitoring
- Mastermind sidecar coordination

## Data Flow

```
Alpha Models → Omega Controllers → Mastermind Sidecar → Shadow Infrastructure
```
