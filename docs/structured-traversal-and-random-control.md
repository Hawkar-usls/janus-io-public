# Structured Traversal And Random Control

## Thesis

JANUS is a structured traversal benchmark for Proof-of-Work search space.

The project does not claim a SHA-256 break, nonce prediction, or a guaranteed
block-finding shortcut. It studies a narrower engineering question:

```text
Can adaptive nonce/job/lane traversal produce a measurably different
accepted-share rare-tail telemetry profile than naive random traversal,
when both are normalized by checked work volume?
```

In other words, JANUS treats blind brute force as the baseline, not the final
form of the method. The project explores whether the traversal layer around
SHA-256 can be made more structured, observable, and resource-aware.

## Why This Matters

Most simple CPU miners treat search as flat random or linear traversal. JANUS
tests whether the traversal policy itself can be made more rational:

- lane ecology instead of one flat walk;
- sector rotation instead of one uniform sweep;
- feedback from accepted-share rare tails;
- desktop-aware pressure control instead of maximum load at any cost;
- inline random-control accounting under the same machine, pool, wire, and
  foreground workload.

This framing is intentionally about traversal policy and telemetry. It is not a
claim about weakening SHA-256.

The desired result is not a dramatic slogan. The desired result is a repeatable
measurement:

```text
structured traversal produces a different rare-tail profile per MH than random
traversal under the same run conditions.
```

## Evidence Standard

Raw counts are not enough. JANUS comparisons should be normalized by checked
work volume:

```text
zN_per_MH = count(zN+) / checked_MH
```

Minimum fields for a useful comparison:

- `checked_MH`
- `accepted`
- `z28+/MH`
- `z30+/MH`
- `z32+/MH`
- `z33+/MH`
- `z34+/MH`
- `max_z`
- `reject_rate`
- `stale_drops`
- `reconnect_count`
- `cooldown`
- `proofmind_mode`
- `desktop_load_state`

## A9 Inline Control

A9 keeps the V32 broad scheduler behavior and adds fresh-only accounting:

```text
janus_broad_mixture = all non-control scheduler lanes
random_control      = explicit random_baseline lane
```

The inline random-control lane does not receive equal exposure by default. In
the V32/A9 mix, `random_baseline` is intentionally small so the main broad
mixture is not replaced by a control experiment. Because exposure is unequal,
A9 must compare per-MH rates, not raw counts.

Fair wording:

```text
A9 is an inline same-run random-control sanity check.
It is not a final equal-exposure A/B benchmark.
```

## Future Equal-Exposure Gate

For a stronger public claim, run a separate control:

```text
A9.1 Equal Exposure Control
50% JANUS broad mixture
50% pure random_baseline
same wire
same machine
same pool
same desktop-load policy
same wall-time or same checked-MH target
```

This is not required for internal iteration, but it reduces ambiguity for
public review.

## A9.11 Strict 50/50 Control

A9.11 implements the equal-exposure idea as a stricter live benchmark:

```text
50% JANUS traversal
50% randomized traversal mirror
same frozen wire
same pool/job stream
same checked-work budget
same submit policy
```

The mirror is not a second product mode. It is the control surface. JANUS may
change only its own phase policy through the Active SovereignGate; the mirror
and the Stratum wire remain untouched.

Fair wording:

```text
A9.11 is a strict same-run 50/50 traversal benchmark. It compares JANUS
rare-tail telemetry against a randomized traversal mirror under equal hash
budget and frozen wire policy.
```

## Publication Boundary

Safe public wording:

```text
JANUS studies whether adaptive PoW scheduler traversal can improve rare-tail
telemetry per MH compared with random traversal under controlled run
conditions.
```

Avoid public wording:

```text
SHA-256 is broken.
JANUS predicts winning nonces.
Rare accepted shares imply a BTC block.
```

## Current Direction

The immediate path is:

1. Keep A9.11 running long enough for meaningful fresh accepted-share corpus
   windows.
2. Summarize A9.11 with JANUS vs randomized traversal mirror tables.
3. Keep raw `janus_io_o1_runs/A9_*` artifacts private.
4. Publish only curated summaries after scrub review.
5. Treat isolated rare tails as signals to reproduce, not final proof.

## Long-Term Framing

If repeated A9/A9.1 windows support the signal, JANUS should be described as a
step toward practical traversal science for hash-search spaces:

```text
less blind walking
more measured traversal
same frozen wire
same SHA-256
better accounting of where rare tails appear
```
