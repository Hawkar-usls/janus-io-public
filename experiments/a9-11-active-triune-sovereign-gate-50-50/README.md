# A9.11 Active Triune Sovereign Gate 50/50

## Purpose

A9.11 tests JANUS traversal against a randomized traversal mirror under equal
checked-work exposure.

```text
JANUS half: structured traversal with Active SovereignGate phase control
mirror half: randomized traversal mirror
wire: frozen
control: same-run strict 50/50
metric: accepted-share rare-tail telemetry
```

The run does not claim a SHA-256 break. It studies traversal behavior.

## Control Boundary

- same runner family;
- same pool/job environment;
- same local submit policy;
- same frozen wire;
- same checked-work budget per side;
- mirror receives no JANUS phase feedback;
- Active SovereignGate can affect only the JANUS half.

## R1 Clean 2000-Gate

Window:

```text
2026-06-06T03:44:00Z..2026-06-06T06:30:41Z
accepted-share corpus: 2004
```

| side | accepted | best_z | z30+ | z32+ | z33+ | z34+ | z36+ | z37+ |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| JANUS | 1012 | 37 | 10 | 3 | 3 | 1 | 1 | 1 |
| randomized traversal mirror | 992 | 32 | 5 | 2 | 0 | 0 | 0 | 0 |

Primary observation:

```text
JANUS held the run best tail and all z33+ accepted-share events.
```

## R2 Fresh Reproduction Snapshot

Fresh boundary:

```text
fresh_started_at_utc: 2026-06-06T15:32:08Z
old archive before boundary: 2273 accepted proof files
```

Snapshot:

```text
snapshot_written_at_utc: 2026-06-06T18:40:23Z
accepted-share corpus: 2456
reject_rate: about 0.16%
reconnects: 0
stale_drops: 0
cooldown: false
phase: JANUS_WAKE
```

| side | accepted | best_z | z30+ | z32+ | z33+ | z34+ |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| JANUS | 1242 | 34 | 10 | 3 | 1 | 1 |
| randomized traversal mirror | 1214 | 33 | 15 | 2 | 2 | 0 |

Primary observation:

```text
The mirror received an early z33, JANUS entered recovery/re-scout behavior,
woke on a z32 anchor, and later took the best-z lead with z34.
```

## R3 7000-Gate Snapshot

Curated snapshot:

- [snapshot-2026-06-07-7000.md](snapshot-2026-06-07-7000.md)

```text
snapshot_written_at_utc: 2026-06-07T10:05:38Z
fresh_started_at_utc: 2026-06-06T22:27:59Z
accepted-share corpus: 7016
reject_rate: about 0.327%
hps_ewma: about 2.52 MH/s
phase: JANUS_WAKE
reason: accepted_z32_anchor
frozen wire: wire_change_required=False
```

| side | accepted | best_z | z30+ | z32+ | z33+ | z34+ | z35+ | z36+ | z37+ | z38+ |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| JANUS | 3519 | 36 | 32 | 10 | 7 | 5 | 2 | 1 | 0 | 0 |
| randomized traversal mirror | 3497 | 33 | 24 | 3 | 2 | 0 | 0 | 0 | 0 | 0 |

Primary observation:

```text
At the 7000-gate snapshot, JANUS holds best_z=36 and leads the randomized
traversal mirror at z32+, z33+, z34+, z35+, and z36+ under frozen wire.
```

## Current Interpretation

R1 remains the sharpest single-tail window because it contains the JANUS z37
event. R3 is the larger publication-gate corpus and is the best current
summary for public review because it preserves the same control boundary at a
larger accepted-share corpus size. R2 is still useful because it reproduces the
state machine behavior and preserves a JANUS best-z lead at the snapshot.

The current evidence is promising but should not be overstated. Stronger public
release material should wait for either:

- repeated JANUS best-z wins;
- repeated JANUS z34+ or z36+ events;
- a scrubbed proofpack with manifest and checksums.

## Public Claim Boundary

Allowed:

```text
JANUS shows repeat-window evidence that structured traversal can produce a
different accepted-share rare-tail profile than a randomized traversal mirror.
```

Not allowed:

```text
SHA-256 is broken.
JANUS predicts nonce values.
The z-tail event is a BTC block.
One accepted-share tail proves a law.
```
