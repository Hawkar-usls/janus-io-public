# Rare-Tail Timing Monitor

Status: integrated observer layer.

JANUS now records timing for accepted rare tails as a first-class pool
understanding metric. This is not a scheduler shortcut and not a wire change.
It is a separate derived telemetry layer that answers a question the normal
accepted-share count cannot answer:

```text
when did the rare tail arrive, under which pool job, and from which branch?
```

## Why It Exists

Accepted-share rare-tail telemetry is probabilistic. A single z35 or z36 event
is not enough to prove a scheduler rule. But a long corpus with timestamps,
pool job context, and branch labels can show whether certain hours, job ages,
network states, or traversal modes deserve a controlled follow-up experiment.

This monitor is therefore bridge material for Avengers:

```text
accepted proof -> timing event -> hourly corpus -> later policy hypothesis
```

The current runner uses it only as an observer. The data may become useful to a
future Avengers scheduler, but only after enough corpus exists and a separate
experiment is defined.

## What It Writes

For z32+ accepted shares by default, the runner writes:

| artifact | purpose |
| --- | --- |
| `*_rare_tail_timing_z32_plus.jsonl` | append-only event stream |
| `*_rare_tail_timing_z32_plus.csv` | table for spreadsheets and graphs |
| `*_rare_tail_timing_summary.json` | dashboard summary by Kyiv hour and branch |

A10.3 Avengers runs use A10.3-prefixed names, for example:

```text
rblganul_a10_3_avengers_kombucha_stress_rare_tail_timing_z32_plus.jsonl
rblganul_a10_3_avengers_kombucha_stress_rare_tail_timing_z32_plus.csv
rblganul_a10_3_avengers_kombucha_stress_rare_tail_timing_summary.json
```

On resume, the embedded monitor also scans the run `proofs/` directory for
existing z32+ accepted proof files and backfills missing timing rows. This keeps
the timing corpus aligned with the accepted-share corpus instead of starting
from zero after a pause.

## Fields

Each event records:

- UTC accepted time and Kyiv local hour;
- zbits and proof filename;
- JANUS or randomized traversal mirror group;
- lane, strategy, sector, config, round, worker;
- Stratum job id, job sequence, clean flag, and notify age at accepted time;
- pool diff and pool z approximation;
- pool response result;
- `scheduler_effect=observe_only`;
- `wire_change_required=false`.

## Boundaries

The monitor does not:

- alter SHA-256 or double-SHA256 hashing;
- alter header construction, nonce wire, target, or Stratum submit behavior;
- feed randomized traversal mirror hints;
- rewrite accepted proof artifacts;
- decide task scheduling in the current A10.3 run.

It is a pool/corpus lens. The point is to accumulate enough time-aware evidence
to decide whether future scheduler hypotheses are worth testing honestly.
