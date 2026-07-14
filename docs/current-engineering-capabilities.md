# Current engineering capabilities

**Status date:** 2026-07-14  
**Claim level:** engineering and telemetry only

This document states what the current JANUS measurement architecture can do,
what evidence supports each capability, and what must not be inferred from it.

## Capability matrix

| Capability | Present | What it establishes | What it does not establish |
|---|---:|---|---|
| Runtime SHA-256 identity checks | Yes | The inspected files match expected digests at the check boundary. | That the machine, interpreter, operating system, or source telemetry is trustworthy. |
| Deterministic instrumentation manifest | Yes | The instrumentation procedure and resulting file can be bound to known digests and declared semantic invariants. | A mathematical proof that every possible runtime behavior is unchanged. |
| Exact completed-batch exposure | Yes | Completed batches can carry exact integer checked-hash counts. | That assigned, queued, cancelled, stale, or unknown-utility work is automatically classified. |
| Exposure reconciliation | Yes | `mine_result_checked`, committed deltas, unique batch identifiers, and partition counters can be cross-checked. | That unavailable counters should be treated as zero. |
| Linked JSONL evidence ledgers | Yes | Silent record mutation, deletion, insertion, or reordering after commitment can be detected when the chain and genesis contract are preserved. | That the original observation was true, complete, independent, or correctly timestamped. |
| Tail metadata validation | Yes | Tail counts, thresholds, event identifiers, and monotonic bucket relationships can be checked for internal consistency. | That a rare tail implies predictability or causal advantage. |
| Sealed/overflow separation | Yes | The frozen target window can be separated from later committed batches. | That every overflow hash was useless to the pool or wasted energy. |
| Fail-closed decisions | Yes | Missing or inconsistent required evidence blocks promotion to a stronger result. | That every possible failure mode has been detected. |
| Runtime health reporting | Partial | Available process exits, hashrate samples, reconnects, stale events, and diagnostic counts can be summarized. | Clean energy, temperature, or device-utilization attribution when telemetry is absent or contaminated. |
| Privacy scan | Yes | Common private paths, endpoints, key markers, and selected credential patterns can be detected in exported text artifacts. | Complete secret detection or formal data-loss prevention. |
| Independent replication framework | Partial | Studies can separate calibration, discovery, challenge, and replication states. | That every historical run was independently acquired or externally replicated. |
| Windows orchestration | Yes | PowerShell can prepare isolated temporary runtime state, execute preflight checks, and launch Python supervision. | Full operating-system portability. |
| Linux/macOS runner | No canonical public equivalent | — | Cross-platform production readiness. |

## Architectural separation

The current architecture uses a useful division of responsibility:

### PowerShell orchestration

Typical responsibilities include:

- resolving project and runtime paths;
- selecting a Python interpreter;
- checking policy and runtime prerequisites;
- preparing an isolated temporary runtime;
- validating file identities and instrumentation manifests;
- preventing unintended duplicate live execution;
- translating child-process results into operator-facing status;
- cleaning temporary state with guarded path checks.

### Python supervision

Typical responsibilities include:

- launching and observing the instrumented runtime;
- collecting exact completed-batch events;
- separating sealed and overflow work;
- constructing normalized evidence ledgers;
- validating event chains and tail metadata;
- reconciling exact exposure and process counters;
- classifying intentional shutdown versus spontaneous failure;
- producing machine-readable final decisions and review reports.

This separation is a strength because environment preparation and measurement
logic can be reviewed independently. It is not, by itself, proof of production
readiness.

## Accurate interpretation of hash chains

JANUS evidence chains are best described as **tamper-evident observer ledgers**.
When implemented correctly, a record references the digest of its predecessor:

```text
genesis -> record 1 -> record 2 -> ... -> final digest
```

A passing verification can support the statement:

> The committed sequence has not been silently rewritten relative to the
> preserved chain contract.

It cannot support the stronger statement:

> Every source event was true and the collection was complete.

That stronger conclusion additionally requires source authentication, clock and
collection controls, acquisition independence, completeness checks, and a clear
threat model.

## Assessment of external praise

The following descriptions are substantially supported:

- the system emphasizes data integrity rather than only dashboard convenience;
- runtime component identities are checked;
- instrumentation is manifest-bound and designed to be reproducible;
- exact exposure and tail metadata are validated semantically;
- privacy and policy checks are integrated into publication workflows;
- negative and inconclusive outcomes are preserved.

The following descriptions are not yet established and should not be used as
factual public claims:

- “ready for production”;
- “forensic proof” without a defined legal and acquisition standard;
- “no direct analogues” without a systematic prior-art and market review;
- “a new industry standard”;
- “cryptographically guarantees that the miner worked honestly”;
- any claim that the architecture proves SHA-256 predictability, mining
  superiority, or energy savings.

## Current engineering value

The defensible value proposition is:

> JANUS turns experimental PoW telemetry into reviewable evidence packages with
> explicit provenance, exact-work accounting, integrity checks, uncertainty,
> and fail-closed claim gates.

This places the project closer to reproducible measurement infrastructure than
to a conventional mining dashboard, while leaving broad market uniqueness and
production suitability open for independent review.
