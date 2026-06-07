# A9.11 Active Triune Sovereign Gate 50/50 Evidence Draft

## Status

Private evidence draft. Do not publish raw run folders, proof archives, wallet-like
worker labels, local paths, or live dashboards without a scrubbed proofpack.

This document summarizes the current A9.11 line as a controlled traversal
benchmark:

```text
same Stratum wire
same local machine
same pool endpoint
same effective submit threshold
strict 50/50 checked work
JANUS traversal vs randomized traversal mirror
```

JANUS does not claim a SHA-256 break. The claim under test is narrower:

```text
structured traversal can produce a measurably different accepted-share
rare-tail telemetry profile than randomized traversal under equal hash budget.
```

## Frozen Wire Boundary

A9.11 keeps the mining wire frozen:

- no header semantics change;
- no nonce submit format change;
- no extranonce policy change;
- no target rule change;
- no SHA-256 change;
- no allocator enable.

Active logic is limited to the JANUS half of the scheduler. The randomized
traversal mirror is kept as the control half.

## Run R1: 2000-Gate Clean Result

Window:

```text
2026-06-06T03:44:00Z..2026-06-06T06:30:41Z
fresh accepted-share corpus: 2004
```

Result:

| side | accepted | best_z | z30+ | z32+ | z33+ | z34+ | z36+ | z37+ |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| JANUS | 1012 | 37 | 10 | 3 | 3 | 1 | 1 | 1 |
| randomized traversal mirror | 992 | 32 | 5 | 2 | 0 | 0 | 0 | 0 |

Important anchor:

```text
accepted_2026-06-06_04-11-58_z37_nonce0x911a83ee_job6a16078a0000748b.json
group=janus_bunnyhop_scout
lane=janus_bunnyhop_scout:zim_reverse_s6
wire=frozen
```

Interpretation:

R1 is the strongest A9.11 evidence candidate so far: JANUS produced the highest
rare-tail event and held every z33+ event in the run.

## Run R2: Fresh Reproduction In Progress

Fresh boundary:

```text
fresh_started_at_utc: 2026-06-06T15:32:08Z
old archive before boundary: 2273 accepted proof files
```

Current snapshot:

```text
snapshot_written_at_utc: 2026-06-06T18:23:58Z
fresh accepted-share corpus: 2250
reject_rate: about 0.18%
socket: alive
reconnects: 0
stale_drops: 0
cooldown: false
phase: JANUS_WAKE
reason: accepted_z32_anchor
```

Result at this snapshot:

| side | accepted | best_z | z30+ | z32+ | z33+ | z34+ |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| JANUS | 1140 | 34 | 10 | 3 | 1 | 1 |
| randomized traversal mirror | 1110 | 33 | 13 | 2 | 2 | 0 |

Interpretation:

R2 does not yet reproduce the R1 z37 column, but it does reproduce a key
structural behavior: the mirror received an early z33, JANUS entered re-scout,
then JANUS woke on a z32 anchor and later took the best-z lead with z34.

This is useful evidence because it shows the state machine working without
changing the frozen wire or contaminating the control half.

## Run R3: 7000-Gate Publication Snapshot

Fresh boundary:

```text
fresh_started_at_utc: 2026-06-06T22:27:59Z
run: A9_11_V32_ACTIVE_TRIUNE_SOVEREIGN_GATE_50_50_AFTER_A9_10
```

Gate snapshot:

```text
snapshot_written_at_utc: 2026-06-07T10:05:38Z
fresh accepted-share corpus: 7016
reject_rate: about 0.327%
hps_ewma: about 2.52 MH/s
cooldown: false
phase: JANUS_WAKE
reason: accepted_z32_anchor
frozen wire: wire_change_required=False
```

Result at this snapshot:

| side | accepted | best_z | z30+ | z32+ | z33+ | z34+ | z35+ | z36+ | z37+ | z38+ |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| JANUS | 3519 | 36 | 32 | 10 | 7 | 5 | 2 | 1 | 0 | 0 |
| randomized traversal mirror | 3497 | 33 | 24 | 3 | 2 | 0 | 0 | 0 | 0 | 0 |

WitchHunter dark-tail summary:

```text
highest_dark_z: 29
JANUS dark events: 18
mirror dark events: 17
```

Interpretation:

R3 is the current publication-gate corpus. It does not repeat the R1 z37 tail,
but it preserves a cleaner larger-corpus comparison: JANUS holds the accepted
best tail at z36 and leads the randomized traversal mirror at z32+, z33+, z34+,
z35+, and z36+ while the frozen wire remains unchanged.

The correct public framing is measured accepted-share rare-tail telemetry under
equal-exposure control. It is not a cryptographic shortcut claim.

## Evidence Standard Before Public Release

Do not publish a strong claim from a single dramatic tail. Preferred public
threshold:

- at least two fresh A9.11 windows;
- strict 50/50 checked work;
- low reject pressure;
- no reconnect/stale anomaly explaining the result;
- JANUS best_z above mirror best_z, or JANUS z-tail density above mirror after
  per-MH normalization;
- proofpack generated from curated summaries, not raw `janus_io_o1_runs`.

The R3 7000-gate snapshot satisfies the larger-corpus threshold for a first
curated publication summary. Stronger claims still require repeated windows and
proofpack manifests/checksums.

Preferred public wording:

```text
JANUS does not claim to break SHA-256.
JANUS studies whether structured traversal can produce measurable differences
in accepted-share rare-tail telemetry against a randomized traversal mirror
under equal hash budget and frozen wire policy.
```

## What Not To Publish

- raw proof directories;
- wallet-like worker labels;
- local Windows paths;
- live lockboxes and dashboards without review;
- claims that rare tails are BTC blocks;
- claims that SHA-256 is broken;
- next-stage private ideas before the current evidence pack is complete.
