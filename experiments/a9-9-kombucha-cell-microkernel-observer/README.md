# A9.9 Kombucha Cell Microkernel Observer

This directory contains curated publication material for the A9.9 strict 50/50
traversal benchmark.

A9.9 compares:

```text
JANUS structured traversal
vs
randomized traversal mirror
```

under equal checked work and frozen wire.

The Kombucha Cell Microkernel is observer-only in this experiment. It labels
cell pressure and stability state but does not change the scheduler, nonce
path, submit path, or allocator state.

## Curated Files

- [method note](../../docs/a9-9-kombucha-cell-microkernel-observer.md)
- [snapshot 2026-06-06](snapshot-2026-06-06.md)

## Publication Boundary

Raw evidence remains private by default. Do not publish raw run folders, proof
archives, live dashboards, wallet-like identifiers, or local paths from
`janus_io_o1_runs/` without a separate scrubbed proofpack review.

## Current Public Claim

Safe wording:

```text
A9.9 is a controlled strict 50/50 accepted-share telemetry benchmark. It tests
whether JANUS structured traversal and a randomized traversal mirror produce
different rare-tail telemetry profiles per checked MH under frozen wire.
```

Avoid wording that frames the result as a cryptographic break, nonce
prediction, or block shortcut. The correct claim is about traversal behavior
and accepted-share rare-tail telemetry.
