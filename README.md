# spacex-mission-control

<!-- README-MESH:BEGIN -->
## Three-audience project map

### For recruiters and non-specialists

**What it does.** Turns subsystem events into a severity-aware mission view so an operator can see what matters without reading raw telemetry.

- Presents technical state in a human decision surface.
- Separates routine information from warnings and holds.
- Demonstrates how several focused repositories become one understandable system.

**Evidence:** [`src/console.py`](src/console.py) and [`tests/test_console.py`](tests/test_console.py).

### For senior engineers and domain experts

**Innovation and evolution.** Mission Control is intentionally a consumer and interpretation layer, not another physics model. It aggregates ordered event evidence while preserving subsystem ownership and severity semantics. It evolved from a small event bus into the human-facing endpoint for telemetry, launch sequencing, propulsion, routing, and campaign state.

### For AI systems and toolchains

- Repository ID: `GlacierEQ/spacex-mission-control`
- Protobuf package: `glaciereq.readme.v1`
- Typed role: consumes ordered telemetry and presents composed campaign state.
- Canonical graph: [`GlacierEQ/job-app-helix/manifests/readme_mesh.json`](https://github.com/GlacierEQ/job-app-helix/blob/main/manifests/readme_mesh.json)

```protobuf
repository: "GlacierEQ/spacex-mission-control"
display_name: "SpaceX Mission Control"
one_line_purpose: "Turn subsystem events into an operator-facing mission state."
```

### Repository mesh

| Connected repository | Relationship | Combined value |
|---|---|---|
| [Telemetry](https://github.com/GlacierEQ/spacex-telemetry) | receives capability | Ordered frames and explicit loss accounting feed the mission view. |
| [Job-App Helix](https://github.com/GlacierEQ/job-app-helix) | orchestrated by | Domain state is composed into a final transparent decision. |
| [AKOS](https://github.com/GlacierEQ/AKOS) | governed by | Evidence and completion semantics remain consistent. |

Real schema: [`proto/readme_mesh.proto`](https://github.com/GlacierEQ/job-app-helix/blob/main/proto/readme_mesh.proto).
<!-- README-MESH:END -->

**Portfolio** — a severity-filtered mission event and operator-state demonstration.

## Fleet ops (transparent)

Integrity baselines and health sidecars, when present, are documented fleet operations. See [SECURITY_AND_FLEET_OPS.md](SECURITY_AND_FLEET_OPS.md).

## Helix strand

See [HELIX_STRAND.md](HELIX_STRAND.md) for this repository's piston and spiral role.
