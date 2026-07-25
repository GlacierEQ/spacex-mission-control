# HELIX strand — `spacex-mission-control`

## Law

- **Piston:** local loop: in → work → out
- **Spiral:** pistons in series; every output is the next input
- **Double helix:** two separate spiral engines pointed at the same star
- **Mutual acceleration:** Alpha truth feeds Omega ops; Omega evidence feeds Alpha refinement

## This leaf

| Pair | Spiral | Role | Star |
|------|--------|------|------|
| `flight` | **omega** | Console bus + severity fan-out (ops spiral) | Flight awareness — know the orbit, command the consoles, hear the bus |

### How this accelerates its twin

- **flight:** consumes Alpha output; returns severity/proof that refines Alpha.

## Runtime

```bash
python3 ~/GlacierEQ_Swarm/automations/jobapp_helix_spiral.py run --all
python3 ~/GlacierEQ_Swarm/automations/jobapp_solidify_flipper.py
```

Portfolio doctrine: `~/job-app/HELIX.md`
