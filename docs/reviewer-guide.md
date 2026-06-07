# Reviewer Guide

This guide is for engineers reviewing Janus Io as a public technical artifact.

## Two-Minute Read

JANUS is a Proof-of-Work traversal benchmark.

It does not change SHA-256, Stratum submit semantics, target rules, or nonce
wire format. It compares scheduler traversal policies and records
accepted-share rare-tail telemetry.

Current core question:

```text
Can structured traversal produce a measurably different rare-tail profile than
a randomized traversal mirror under equal hash budget and frozen wire policy?
```

## Five-Minute Method Read

Read:

- `README.md`
- `docs/structured-traversal-and-random-control.md`
- `docs/wire-policy.md`

Key controls:

- frozen wire;
- accepted-share proof artifacts;
- fresh run boundaries;
- strict 50/50 checked work in A9.11;
- randomized traversal mirror as control;
- reject, stale, reconnect, cooldown, and HPS reporting.

## Ten-Minute Evidence Read

Read:

- `docs/a9-11-active-triune-sovereign-gate-50-50.md`
- `experiments/a9-11-active-triune-sovereign-gate-50-50/README.md`
- `docs/evidence-pack-spec.md`

What matters:

- JANUS vs mirror exposure;
- `best_z`;
- `z30+`, `z32+`, `z33+`, `z34+`;
- per-MH normalization where available;
- reject pressure;
- stale drops and reconnects;
- whether a rare tail belongs to JANUS or the randomized traversal mirror.

## Thirty-Minute Verification Read

Review:

- runner sentinel/version;
- frozen wire statements;
- proofpack manifest;
- scrubber output;
- summary tables;
- exact fresh cutoff timestamps;
- negative-result and limitation sections.

Do not use raw `janus_io_o1_runs/` directly as a public artifact. It is private
raw evidence and may contain operational identifiers. Public review should use a
scrubbed proofpack or curated summary.

## Claim Boundary

Allowed:

```text
JANUS is a structured traversal benchmark.
JANUS compares rare-tail telemetry against a randomized traversal mirror.
JANUS keeps the mining wire frozen.
JANUS treats rare tails as telemetry, not proof of a cryptographic break.
```

Not allowed:

```text
SHA-256 is broken.
JANUS predicts nonces.
JANUS found a guaranteed mining shortcut.
A rare accepted share is equivalent to a BTC block.
```
