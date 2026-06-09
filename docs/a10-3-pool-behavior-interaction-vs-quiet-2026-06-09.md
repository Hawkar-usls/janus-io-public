# A10.3 Pool Behavior: Interaction vs Quiet - 2026-06-09

Status: derived offline report from local JANUS telemetry.

No network mining was started by this report. Raw proof artifacts were not rewritten.

## Run

```text
run_dir: A10_AVENGERS_KOMBUCHA_STRESS_JANUS_VS_RANDOM_50_50_PRIVATE
pool: pool.nerdminers.org:3333
pool_diff: 0.001
frozen_wire: wire_change_required=false in dashboard/proof artifacts
```

## Window Model

Interaction windows are explicit operator/Codex activity windows. Quiet is the complement inside the same local run.

```text
interaction: 2026-06-08T15:30:00Z -> 2026-06-08T16:10:00Z  publication/report prep activity window around local Git activity
interaction: 2026-06-08T20:00:00Z -> 2026-06-08T22:32:00Z  glyph observer / pLEA discovery and live review window
interaction: 2026-06-09T00:47:00Z -> 2026-06-09T02:44:47Z  A10 report, pLEA mirror family, restart, live check, and final closeout window
```

## Comparison

| metric | interaction | quiet |
| --- | ---: | ---: |
| `submitted_delta` | `1627` | `7285` |
| `accepted_delta` | `1608` | `7210` |
| `rejected_delta` | `19` | `75` |
| `reject_pct` | `1.1677934849416103` | `1.029512697323267` |
| `job_changes` | `415` | `1251` |
| `unique_jobs_seen` | `417` | `1255` |
| `hps_avg` | `2679509.51` | `2688964.22` |
| `lab_best_z` | `34` | `35` |
| `accepted_proofs` | `1610` | `7210` |
| `proof_best_z` | `34` | `35` |
| `proof_job_age_ms_avg` | `18497.6` | `18506.18` |
| `glyph_rows` | `8938` | `11320` |

## Rare Tails

```text
interaction: {'z23': 1610, 'z24': 810, 'z25': 428, 'z26': 212, 'z28': 53, 'z30': 14, 'z32': 3, 'z33': 2, 'z34': 1}
quiet:       {'z23': 7210, 'z24': 3619, 'z25': 1791, 'z26': 892, 'z28': 206, 'z30': 55, 'z32': 14, 'z33': 5, 'z34': 2, 'z35': 1}
```

Normalized per 1000 accepted proofs:

```text
interaction: {'z23': 1000.0, 'z24': 503.1056, 'z25': 265.8385, 'z26': 131.677, 'z28': 32.9193, 'z30': 8.6957, 'z32': 1.8634, 'z33': 1.2422, 'z34': 0.6211}
quiet:       {'z23': 1000.0, 'z24': 501.9417, 'z25': 248.405, 'z26': 123.7171, 'z28': 28.5714, 'z30': 7.6283, 'z32': 1.9417, 'z33': 0.6935, 'z34': 0.2774, 'z35': 0.1387}
```

## Groups

```text
interaction: {'janus_bunnyhop_scout': 456, 'randomized_traversal_mirror': 820, 'janus_bunnyhop_rescout': 115, 'unknown': 161, 'janus_broad_mixture': 58}
quiet:       {'janus_bunnyhop_scout': 606, 'randomized_traversal_mirror': 3640, 'unknown': 1533, 'janus_bunnyhop_rescout': 918, 'janus_broad_mixture': 513}
```

## Glyph Families

```text
interaction rows: {'plea_mirror_family': 20}
interaction job_id|ntime: {'plea_mirror_family': 1}
quiet rows: {}
quiet job_id|ntime: {}
```

## Current Signal

```text
interaction z33/z34 per 1000: 1.2422 / 0.6211
quiet z33/z34/z35 per 1000: 0.6935 / 0.2774 / 0.1387
interaction reject_pct: 1.1677934849416103
quiet reject_pct: 1.029512697323267
interaction job_age_ms_avg: 18497.6
quiet job_age_ms_avg: 18506.18

Current reading: interaction windows show slightly higher z33/z34 density,
but quiet windows still hold the single z35 and overall best_z. Reject%
is also slightly higher during interaction. Job age is essentially equal.
The pLEA/AELp family appears only inside interaction windows so far,
but only as one independent job_id|ntime source.
```

## Preliminary Reading

```text
This report can show correlation windows, not pool memory or intent.
The current strongest falsifiable question is whether JANUS-active windows
produce a repeatable shift in reject%, job-age-at-accept, z-tail density,
or independent glyph-family repeats compared with quiet windows.
```
