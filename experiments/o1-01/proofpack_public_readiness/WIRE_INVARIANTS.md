# Wire Invariants

Janus V31 IO evidence should be presented as wire-safe Stratum experimentation. The scheduler may change nonce-space allocation, but accepted-compatible wire behavior remains frozen.

## Frozen Invariants

- Submit nonce is big-endian uint32 hex.
- Header nonce bytes are little-endian.
- Prevhash uses the accepted word-reverse mirror.
- Extranonce2 is little-endian in the accepted configuration.
- Canonical submit path is pool-reconstructable.
- TruthGate blocks non-submit-compatible configurations before submit.
- Submit gate follows pool target policy and configured local gate.
- Accepted proof format is not changed by scheduler experiments.

## Required Public Claim

Use:

```text
wire_change_required=false
```

Do not claim a scheduler result required wire mutation. If a future experiment changes wire policy, it must be labeled as a separate incompatible experiment.
