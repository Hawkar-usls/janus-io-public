# A9 V32 Broad Mixture Random Control

## Purpose

A9 tests the current JANUS direction without changing the frozen wire path:

```text
V32 broad scheduler mixture
+ fresh-only accounting
+ inline random_baseline control
+ desktop-load state tracking
```

The goal is to measure whether the JANUS broad mixture produces a different
accepted-share rare-tail profile than random traversal under the same run
conditions.

## Scope

A9 is a private research runner until a reviewed summary is prepared.

Raw run artifacts stay under:

```text
janus_io_o1_runs/A9_V32_BROAD_MIXTURE_RANDOM_CONTROL_AFTER_V32
```

Do not publish that raw folder by default.

## Fixed Invariants

- Stratum wire is frozen.
- Header construction is frozen.
- Nonce submit path is frozen.
- Extranonce and prevhash policy are frozen.
- Allocator is not enabled.
- Theta/Ramanujan phase logic is not enabled.
- A9 accounting does not choose tasks or change scheduler weights.

## Accounting Groups

```text
janus_broad_mixture:
  linear_proof
  janus_dispatcher
  dual_lock
  zim_reverse_s6

random_control:
  random_baseline
```

The default V32/A9 mix gives random control about 5% exposure. That is enough
for an inline sanity check, but raw counts must not be compared directly.

## Metrics

Compare by checked work volume:

```text
accepted/MH
z28+/MH
z30+/MH
z32+/MH
z33+/MH
z34+/MH
z36+/MH
max_z
reject_rate
stale_drops
reconnect_count
cooldown/SURVIVE state
desktop_load_state
```

## Gates

Early gate:

```text
fresh_proofs >= 1000
random_control_mh >= 250
wire_change_required = False
stale_drops = 0
reconnect_count = 0
```

Strong gate:

```text
fresh_proofs >= 5000
random_control_mh >= 1000
reject_rate < 0.5-1.0%
per-MH table complete
raw proof files preserved
summary scrubbed before publication
```

Future strict control:

```text
A9.1 equal-exposure run:
50% JANUS broad mixture
50% random_baseline
```

## Reporting Rule

Use this wording:

```text
A9 produced promising inline random-control evidence.
Because exposure is unequal, all comparisons are normalized by checked MH.
The result is not yet a final equal-exposure proof.
```
