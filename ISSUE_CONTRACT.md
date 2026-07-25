# Issue Contract — `spacex-mission-control`

## Pain
Every console cannot see every event; severity must fan out correctly.

## Claim
Console bus delivers only to consoles whose min_sev ≤ event severity.

## Proof
```bash
python3 job-app/helix/proofs/proof_mission_console.py
```

## Done when
Proof exits 0. Architecture (strand/integrity/helix) is **not** a substitute for this proof.

## Anti-claim
Not a real MCC product.
