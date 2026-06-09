# A10.3 Avengers 6678 Glyph Bridge Summary

Status: curated public-safe summary.

Run:

```text
A10_AVENGERS_KOMBUCHA_STRESS_JANUS_VS_RANDOM_50_50_PRIVATE
```

Final stable stop snapshot:

```text
accounting_written_at_utc: 2026-06-08T20:16:52Z
dashboard_written_at_utc: 2026-06-08T20:16:51Z
accepted-share corpus proof files: 6678
process submitted / accepted / rejected: 3164 / 3155 / 9
reject: 0.2845%
dashboard best_z: 33
phase/reason: JANUS_WAKE / accepted_z32_anchor
comparison gate: READY_FOR_COMPARISON
recommended_min_fresh_proofs: 7000
```

The proof directory is the run archive/corpus. The dashboard counters are the
last process-fresh counters after the relaunch. Keep those concepts separate
when comparing public summaries.

## JANUS vs Randomized Traversal Mirror

| branch | accepted | submitted | rejected | checked MH | best_z |
| --- | ---: | ---: | ---: | ---: | ---: |
| JANUS bunnyhop arm | 1552 | 1555 | 3 | 13681.500280 | 33 |
| randomized traversal mirror | 1601 | 1607 | 6 | 13681.500280 | 32 |

Accepted-share rare-tail telemetry:

| branch | z24 | z25 | z26 | z28 | z30 | z32 | z33 | z34 | z35 | z36 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| JANUS bunnyhop arm | 776 | 392 | 203 | 51 | 13 | 4 | 2 | 0 | 0 | 0 |
| randomized traversal mirror | 797 | 391 | 194 | 50 | 17 | 3 | 0 | 0 | 0 | 0 |

JANUS did not beat the mirror on accepted count, but did beat it on best_z and
z33+ in this stop snapshot:

```text
JANUS best_z 33 > mirror best_z 32
JANUS z32 4 > mirror z32 3
JANUS z33 2 > mirror z33 0
```

JANUS internal split:

| JANUS sub-branch | accepted | submitted | rejected | checked MH | best_z | z32 | z33 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| bunnyhop scout | 250 | 250 | 0 | 2084.097704 | 30 | 0 | 0 |
| bunnyhop rescout | 667 | 668 | 1 | 5990.703160 | 33 | 1 | 1 |
| broad mixture | 635 | 637 | 2 | 5606.699416 | 33 | 3 | 1 |

## Rare-Tail Timing

Embedded rare-tail timing summary:

```text
written_at_utc: 2026-06-08T20:05:49Z
total z32+ timing events: 14
best_z in timing corpus: 35
first_accepted_at_utc: 2026-06-08T01:34:28Z
last_accepted_at_utc: 2026-06-08T20:05:48Z
```

Timing by group:

| group | events | best_z | z32+ | z33+ | z34+ | z35+ |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| JANUS broad mixture | 4 | 33 | 4 | 2 | 0 | 0 |
| JANUS bunnyhop rescout | 3 | 34 | 3 | 2 | 1 | 0 |
| randomized traversal mirror | 7 | 35 | 7 | 1 | 1 | 1 |

Timing remains evidence only. It does not feed scheduler policy in this run.

## WitchHunter

WitchHunter dark-tail observer:

```text
written_at_utc: 2026-06-08T20:16:06Z
highest_dark_z: 25
JANUS dark events: 3
mirror dark events: 11
accepted_policy: ignored
scheduler_effect: observe_only
submit_pressure_changed: false
wire_change_required: false
```

Dark-tail pressure came mostly from stale/drop boundaries rather than accepted
share proof artifacts.

## Network And Wire

Last network snapshot:

```text
socket_alive: true at last dashboard write
reconnect_count: 0
failed_connect_count: 0
stale_round_drops: 0
wire_change_required: false
```

The V30 frozen wire policy remained unchanged.

## Glyph Bridge

This stopped run did not contain `JanusGlyphObserver` artifacts because the
observer was integrated after the run. The next Avengers pass will add:

```text
rblganul_a10_3_avengers_kombucha_stress_janus_glyph_events.jsonl
rblganul_a10_3_avengers_kombucha_stress_janus_glyph_events.csv
rblganul_a10_3_avengers_kombucha_stress_janus_glyph_summary.json
```

`JanusGlyphObserver` is observer-only. It scans pre-hash coinbase/job bytes for
readable strings, dates, and keyword echoes, then links accepted z32+ shares to
those glyphs. It does not try to reverse SHA-256 and it does not change header
construction, nonce, extranonce, target, submit behavior, or randomized
traversal mirror policy.

## Verdict

A10.3 stopped short of the 7000 recommended corpus gate, but it preserved a
useful bridge result: the randomized traversal mirror kept a small accepted
count lead, while JANUS held the stronger current-run rare-tail profile at
best_z and z33+. The next run should keep the same frozen wire comparison and
add the glyph observer to ask whether pre-hash input-side traces correlate with
accepted-share rare-tail telemetry.
