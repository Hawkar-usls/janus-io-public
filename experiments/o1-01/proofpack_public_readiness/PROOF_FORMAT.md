# Accepted Proof Format

Accepted proof files are JSON artifacts saved when a share is accepted by the pool. They are intended to preserve enough information for independent reconstruction and verification.

Typical top-level fields:

- `created_at_utc`
- `hash`
- `header`
- `job`
- `miner`
- `nonce`
- `pool`
- `proof_type`
- `raw_candidate`
- `sentinel`
- `submit`
- `version`

## Important Fields

`hash` records the displayed double-SHA256 value, raw hash form, target pass state, and zbits.

`header` records the 80-byte header hex and merkle root details.

`job` records Stratum notify fields needed for reconstruction.

`miner` records scheduler attribution such as strategy, lane, sector, cfg, worker, and wire lock.

`nonce` records extranonce, header nonce bytes, integer nonce, ntime, and submit nonce.

`submit` records mirror verification and submit parameters.

## Public Handling

Before public release, proofs should be checked for accidental private data. Public examples should avoid exposing private account details beyond what is already intentionally public for the experiment.

Proof files should not be rewritten during documentation cleanup.
