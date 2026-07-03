# A18.11 Historic Tail Revival

Status: **healthy research run / telemetry only**.

A18.11 is a public-safe checkpoint of the current JANUS scheduler profile that
showed the strongest early normalized signal in the A17.8 / HRain line. It is
not a new hash function and it does not change pool wire behavior.

```text
WIRE/HASH/SUBMIT: frozen
Mirror: strict randomized 50/50 control
Claim level: telemetry only, no advantage/profit/superiority claim
```

## Intent

A18.11 keeps the balanced A18.4-style revival profile, then seeds the scheduler
with historical rare-tail route memory so JANUS does not optimize against deep
tails while chasing ordinary accepted shares.

The goal is to compare:

```text
JANUS structured traversal / MH
vs
randomized traversal mirror / MH
```

The public claim boundary remains strict: early positive telemetry is a signal
to reproduce, not proof of superiority.

## Public-Safe Runtime Shape

```text
HRain observer UI
  -> A18 overlay and accounting
  -> A18.11 scheduler profile
  -> strict 50/50 randomized traversal mirror
```

Private runtime details such as local paths, LAN hosts, wallet labels, pool
credentials, raw accepted-share logs, and device logs are intentionally omitted
from this public checkpoint.

## Profile Summary

A18.11 uses the same checked-work accounting and the same randomized mirror
control as the earlier A14/A18 line. The distinctive profile knobs are:

```text
a11_exploration_floor = 0.10
a11_historical_prior_weight = 0.07
a14_nav_lock_after_accepted = 6
a14_nav_lock_prob = 0.78
a14_nav_explore_floor = 0.045
a14_nav_topk = 16
a14_nav_min_mh = 0.08
a14_nav_rollback_window = 44
preferred_route_boost = 0.22
```

Lane weighting:

```text
linear_proof_weight = 32
janus_weight = 34
dual_lock_weight = 18
zim_s6_weight = 16
dual_lock_linear_s6_weight = 38
dual_lock_zim_s6_weight = 42
dual_lock_knight_s11_weight = 20
```

The preferred route is stored in the public profile JSON without private runtime
configuration.

## Current Sanitized Snapshot

From the current local run window:

```text
round = 880
submitted = 272
accepted = 269
rejected = 3
reject_rate = 0.0110
best_z = 30
socket_alive = true
reconnect_count = 0
stale_round_drops = 0
```

Strict normalized 50/50:

```text
JANUS:  149 accepted / 1171.643856 MH = 0.1271717504 accepted/MH
Mirror: 120 accepted / 1171.643856 MH = 0.1024202017 accepted/MH
```

Tail telemetry:

```text
JANUS:  best_z=30, z28+=4, z30+=1, z32+=0, z34+=0
Mirror: best_z=28, z28+=2, z30+=0, z32+=0, z34+=0
```

Confidence gate:

```text
effect_size_rate_difference = 0.0247515487
ci95_low = -0.0026849451
ci95_high = 0.0521880426
```

Because the confidence interval still crosses zero and the run is far below the
larger proof target, this checkpoint is **not** an advantage claim.

## Why This Checkpoint Matters

A18.11 is worth preserving because it simultaneously showed:

- a positive normalized `accepted/MH` gap versus the randomized mirror;
- a better early rare-tail profile (`best_z=30` versus mirror `best_z=28`);
- healthy reliability telemetry with no reconnects or stale round drops;
- no modification to WIRE/HASH/SUBMIT or mirror semantics.

The next research step is not to replace A18.11, but to build on it with a
tail-focused overlay such as `A18.12_TAIL_HUNTER_GOVERNED`.

## Claim Boundary

This document preserves a promising scheduler profile. It does not claim:

- mining profit;
- SHA-256 weakness;
- nonce prediction;
- deterministic superiority;
- proof that JANUS is better than random traversal.

A stronger claim would require larger repeated windows, strict equal-work
normalization, z-tail/MH analysis, duplicate accounting, reject accounting, and
confidence gates that no longer overlap zero.
