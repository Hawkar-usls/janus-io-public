# Janus ProofPack README Draft

Janus is an adaptive proof-oriented Stratum research framework. It is designed to study scheduler behavior, rare-tail telemetry, and accepted-share proof collection while keeping wire behavior reproducible and auditable.

Janus does not claim that SHA-256 is broken. It does not claim guaranteed profit. The project should be presented as an experimental scheduler and allocator around standard proof-of-work mechanics.

## Current V31 IO Evidence

- V31 IO reached 10000+ clean accepted proof files.
- V31 IO reached a confirmed z36 accepted proof.
- Reject rate stayed below 0.3 percent around the 10000-proof milestone.
- `wire_change_required=false`.
- Accepted proofs are saved as reproducible JSON artifacts.

Confirmed z36 proof:

```text
accepted_2026-05-26_22-20-16_z36_nonce0x7f517f85_job6a16078a000000b2.json
```

The z36 lane attribution recorded in the lab notes is:

```text
strategy/lane/cfg: linear / linear_proof / canonical
```

## What The Repository Should Demonstrate

- Accepted-share proof files can be verified from saved fields.
- Wire invariants are documented and frozen.
- Rare-tail statistics are counted from proof filenames and proof metadata.
- A/B comparisons can be run against random, linear, Zim, Janus, and DualLock baselines.
- Future allocators can change scheduler weights without changing Stratum wire behavior.

## Future Work

- TachyonMicroAgent adaptive allocator for V32.
- Larger A/B tests versus random, linear, Zim, and NerdMiner-like baselines.
- Public proof verifier and reproducible benchmark scripts.
