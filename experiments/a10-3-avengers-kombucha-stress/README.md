# A10.3 Avengers Kombucha Stress

This experiment is a controlled JANUS-vs-randomized traversal mirror benchmark.
It keeps the mining wire frozen and changes only scheduler-side traversal,
memory, and batch-pressure choices.

## Public Artifacts

- `snapshot-2026-06-08-2000.md` - curated 2k accepted-share corpus gate snapshot.

## Publication Boundary

This directory contains summaries only. Raw proof files, live accounting state,
pool logs, and proof archives stay outside the public summary layer.

## Mechanic Under Test

A10.3 adds a stress-molecule layer to the Kombucha scheduler memory. The stress
layer reacts to mirror pressure and JANUS rare-tail recovery, but it does not
change SHA, Stratum, share target logic, accepted proof format, or V30 wire
policy.
