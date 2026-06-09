# A10 Encoding Archaeology Status - 2026-06-09

This is a curated public snapshot from the A10 Encoding Archaeology line. It is
not a raw proof archive and does not publish live run state.

## Canonical Status

```text
A10_ENCODING_ARCHAEOLOGY
mode: active evidence gathering
wire: frozen / clean
claim: repeated glyph candidate, rare-tail linked, semantic unconfirmed
```

The important boundary is:

```text
observer archaeology, not message decoding
```

A10 scans pre-hash Stratum/job material and accepted-share context for readable
strings, symbolic glyphs, mirror forms, low-entropy anomalies, and encoded
fragments. Those observations are linked to accepted-share rare-tail telemetry.
They are not fed into the wire path and do not alter submit behavior.

## 2026-06-09 Checkpoint

Latest curated check used for this public note:

```text
run: A10_ENCODING_ARCHAEOLOGY_THE_AVENGERS
written_at_utc: 2026-06-09T20:40:18Z
accepted-share corpus: 377
submitted: 396
rejected: 3
reject_rate: 0.758%
mode: HUNT
load_state: DESKTOP_LOAD
wire_change_required: false
```

JANUS side:

```text
accepted: 199
best_z: 31
tails: z23=199 z24=97 z25=52 z26=30 z28=8 z30=4 z32=0
```

Randomized traversal mirror:

```text
accepted: 178
best_z: 35
tails: z23=178 z24=87 z25=48 z26=31 z28=10 z30=5 z32=2 z33=1 z34=1 z35=1
```

Interpretation:

```text
JANUS currently leads accepted-share mass.
The randomized traversal mirror owns the current peak rare tail.
z28/z30 are comparable; z32+ is not yet a JANUS win in this run.
```

## Glyph Watchlist

Main watchlist:

```text
VV<~ / ~<VV
```

Observed status:

```text
VV<~: 11 event rows, 7 unique jobs, max z28
~<VV: 8 event rows, 4 unique jobs, max z28
status: repeated glyph candidate, rare-tail linked, semantic unconfirmed
```

Secondary watchlist:

```text
KRRO: 2 event rows, 1 unique job, max z30, MIRROR_GLYPH, strong candidate
&&fU: 4 event rows, 1 unique job, max z32, encoded fragment candidate
```

Hold:

```text
pLEA / AELp / key
```

These remain useful historical artifacts, but they did not repeat in the latest
targeted A10 scan.

## Promotion Gates

The next meaningful gate events are:

```text
1. VV<~ or ~<VV repeats on a new job_id with z28+
2. KRRO repeats on a new job_id
3. &&fU repeats outside its original job_id
4. JANUS produces a new z32+
```

Until then, A10 remains an observer-only archaeology layer. It preserves clean
evidence, not confirmed semantic messages.

## Evidence Boundary

Public summaries must keep:

```text
generated reports separate from raw logs
accepted-share proof artifacts private unless curated
frozen wire unchanged
claim discipline explicit
```

The public claim is deliberately narrow:

```text
repeated glyph candidate
rare-tail linked
semantic unconfirmed
no SHA-256 break claim
```
