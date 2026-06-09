# A10.3 Final Run Closeout - Avengers Kombucha Stress

This is a curated closeout report, not a raw proof archive. Raw proof files and
live run state remain local/private under `janus_io_o1_runs/`.

## Run

```text
run: A10_AVENGERS_KOMBUCHA_STRESS_JANUS_VS_RANDOM_50_50_PRIVATE
version: Rblganul A10.3 Avengers Kombucha Stress Strict 50_50 IO SINGLE 20260608
mode: JANUS vs randomized traversal mirror, strict 50/50
objective: observe JANUS rare-tail telemetry and pre-hash glyph artifacts without changing the mining wire
host: pool.nerdminers.org:3333
fresh_started_at_utc: 2026-06-09T02:08:50Z
dashboard_written_at_utc: 2026-06-09T02:44:23Z
accounting_written_at_utc: 2026-06-09T02:44:32Z
```

## Fresh Segment Snapshot

These counters are process-fresh for the last restarted segment.

```text
uptime_seconds: 2094.338
submitted: 57
accepted: 56
rejected: 1
reject_rate: 1.7544%
hps_ewma: 2,648,941
best_hps_ewma: 2,711,659
accepted_per_mh: 0.11261
dashboard_best_z: 28
wire_change_required: false
```

Fresh accepted proof files by timestamp from `2026-06-09T02:08:50Z`:

```text
count: 57
latest: accepted_2026-06-09_02-44-33_z24_nonce0x937cbb1e_job6a26ca5a000005d6.json
tails: z23=57 z24=24 z25=13 z26=6 z28=1 z30=0 z32=0 z33=0 z34=0 z35=0 z36=0
```

## JANUS Vs Randomized Traversal Mirror

```text
JANUS arm/scout:
accepted: 31
submitted: 32
rejected: 1
best_z: 28
tails: z23=31 z24=13 z25=6 z26=2 z28=1 z30=0 z32=0 z33=0 z34=0 z35=0 z36=0
accepted_per_mh: 0.123736

randomized traversal mirror:
accepted: 25
submitted: 25
rejected: 0
best_z: 27
tails: z23=25 z24=10 z25=7 z26=4 z28=0 z30=0 z32=0 z33=0 z34=0 z35=0 z36=0
accepted_per_mh: 0.099787
```

Fresh verdict:

```text
JANUS soft lead in this final segment: higher accepted count, higher best_z, and the only z28.
This is not statistically locked; it is a clean final signal worth preserving.
```

## Glyph Observer

```text
summary_written_at_utc: 2026-06-09T02:44:47Z
started_at_utc: 2026-06-09T02:08:51Z
observer_only: true
wire_change_required: false
total_events: 20,180
unique_independent_glyph_keys: 6,821
accepted_link_events: 17,460
best_z_context_seen_by_glyph_observer: 35
job_ntime_key_formula: job_id|ntime
independent_glyph_key_formula: job_id|ntime|source_name|normalized_glyph_text|variant
```

Mirror-family accounting:

```text
plea_mirror_family: events=42 independent_keys=4 job_ntime_count=1
gp_d_mirror_family: events=10 independent_keys=4 job_ntime_count=1
```

Important boundary:

```text
pLEA/AELp remains a structured watchlist artifact, not a confirmed repeated
message. It has multiple event rows and independent keys inside one job/ntime
source. A stronger claim requires a repeat in a different job_id|ntime.
```

Curated artifact note:

```text
docs/a10-3-curated-glyph-artifacts-2026-06-09.md
```

## Pool Behavior Report

The pool behavior comparison is preserved as a hypothesis instrument:

```text
docs/a10-3-pool-behavior-interaction-vs-quiet-2026-06-09.md
docs/a10-3-pool-behavior-interaction-vs-quiet-2026-06-09.json
docs/a10-3-pool-behavior-windows-2026-06-09.json
```

Current interpretation:

```text
JANUS did not prove that the pool "remembers" the operator.
JANUS did prove that we can separate operator-interaction windows from quiet windows
and compare accepted-share rare-tail telemetry, reject%, job churn, and glyph events.
```

## Claim Boundary

Do claim:

```text
observer-only pre-hash glyph telemetry
strict JANUS vs randomized traversal mirror comparison
accepted-share rare-tail telemetry with fresh boundaries
reproducible windowed pool-behavior analysis
clear separation between raw proof archive and public reports
```

Do not claim:

```text
SHA-256 reversal
Bitcoin shortcut
pool intent
Satoshi signal confirmation
guaranteed mining advantage
```

## One-Line Verdict

```text
A10.3 closed with a clean JANUS soft lead in the final fresh segment, an active
observer-only glyph pipeline, and a curated evidence trail ready for public Git
without publishing raw live state.
```
