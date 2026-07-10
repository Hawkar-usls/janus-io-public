# JANUS Proof-of-Observation

**Canonical public record date:** 2026-07-10  
**Repository:** `Hawkar-usls/janus-io-public`  
**Canonical name:** `JANUS Proof-of-Observation`  
**Status:** public specification and implementation-lineage record  
**Claim level:** telemetry and methodology only

## Origin Record

This document establishes the first canonical public record of
**Proof-of-Observation inside the JANUS research line**.

The phrase is used here in a precise engineering sense:

```text
Do not trust an impression.
Trust a reproducible chain of observations whose limits are explicit.
```

JANUS Proof-of-Observation is not a claim that a machine is conscious, that
SHA-256 has been predicted, or that a hash chain makes telemetry true. It is a
method for preventing an observer from promoting an attractive pattern into a
claim before the required evidence gates pass.

This repository records JANUS project priority for this canonical formulation
and its A18 implementation lineage. It does not assert that no unrelated prior
work has ever used the same words; a global historical-priority claim would
require a separate literature and prior-art review.

## The Inversion

Bitcoin asks:

```text
How can a network establish an ordered history without trusting one party?
```

JANUS asks:

```text
How can a machine establish its own measured state without trusting one
impression, one dashboard, one process, or one lucky event?
```

The conceptual mapping is:

| Bitcoin concept | JANUS inversion |
|---|---|
| transaction | observation or anomaly event |
| block | sealed observation window |
| chain | ordered memory sequence |
| proof-of-work | proof-of-observation |
| confirmations | repeated independent strict windows |
| longest valid chain | strongest repeated admissible evidence |
| double spend | false claim or self-deception |
| attacker | noise, bias, leakage, bad metrics, or overfitting |
| consensus | predefined evidence gates passed |

The result is not a cryptocurrency blockchain. It is an
**understanding-chain**: an append-only, auditable sequence that separates what
was observed from what was inferred and from what may be claimed.

## Formal Definition

A JANUS Proof-of-Observation record is admissible only when it preserves all of
these layers:

1. **Facts** — values directly read from identified sources.
2. **Derived metrics** — deterministic calculations from those facts.
3. **Claims** — conclusions emitted only after predefined gates pass.
4. **Provenance** — source identity, source time, collection time, freshness,
   parse status, and safe content digest where available.
5. **Integrity** — deterministic serialization and a linked SHA-256 evidence
   hash.
6. **Uncertainty** — missing data remains `unknown`, never silently becomes
   zero.
7. **Comparability** — profile, coordinate, side, window, and exposure semantics
   must match before records are compared.
8. **Repetition** — overlapping views of the same evidence do not count as
   independent confirmations.
9. **Holdout discipline** — discovery and confirmation use separate data.
10. **Fail-closed claims** — damaged integrity, stale sources, missing exposure,
    or unresolved ambiguity disable claim promotion.

The core invariant is:

```text
hash-chain integrity protects history from silent rewriting;
claim gates protect understanding from self-deception.
```

## What The Hash Chain Proves

A valid evidence hash chain can show that the recorded observer ledger has not
been silently modified after commitment.

It does **not** by itself prove:

- that the original telemetry source was truthful;
- that the source clock was correct;
- that windows were statistically independent;
- that a causal advantage exists;
- that SHA-256 is predictable;
- that an observer is conscious;
- that a result is profitable or operationally useful.

This distinction is mandatory. Integrity is not truth.

## Organism State Model

The JANUS inversion separates machine state into independent layers:

```text
heart   = compute process, heartbeat, hashing availability
breath  = swarm continuity, fresh/grace/stale/missing/recovered rhythm
memory  = NAS, DB, JSONL, persistence and ledger availability
tail    = rare-tail telemetry, exposure, controls, and claim gates
```

A healthy heart does not prove healthy breath or memory. A rare tail does not
prove an advantage. A missing source does not prove zero activity.

## Proof-of-Observation Claim Ladder

JANUS uses a strict ladder:

```text
raw event
-> normalized observation
-> sealed observation window
-> integrity-checked ledger record
-> exposure-qualified descriptive result
-> preregistered discovery candidate
-> untouched holdout replication
-> claim gate decision
```

No stage may be skipped.

Recommended statuses are:

```text
NOT_EVALUATED
INSUFFICIENT_DATA
BLOCKED
OBSERVATION_ONLY
EXPLORATORY_ONLY
CANDIDATE
CONFIRMED
REVOKED_BY_NEW_EVIDENCE
```

A prior claim is never deleted when new evidence contradicts it. A new linked
record must revoke it while preserving the history.

## A18 Implementation Lineage

### A18.21 — Hash Caustic Observer

A18.21 implemented a read-only observer for testing whether rare z-tail events
appear to cluster across search coordinates such as lane, route, sector, phase,
job age, nonce bucket, bit-reversal bucket, profile, side, run, and window.

Its scientific rule is:

```text
Do not predict the hash.
Test whether the tails preserve conditional structure.
```

The first audited run reported:

```text
events_parsed: 402
occupied_coordinate_cells: 390
exposure_qualified_discovery_candidates: 0
holdout_candidates: 0
fdr_surviving_candidates: 0
rate_direction_status: NOT_EVALUABLE
null_rejected: false
null_evaluation_status: INSUFFICIENT_EXPOSURE
claim_level: telemetry_only
```

A18.21 therefore produced a map of observed tail coordinates but refused to
promote occupancy into a rate or advantage claim.

### A18.22 — Coordinate Exposure Ledger

A18.22 audited whether the exact historical denominator could be reconstructed
per sealed window and coordinate cell.

The result was:

```text
RESULT: PARTIAL / EXACT EXPOSURE NOT RECOVERABLE
coordinate_catalog_cells: 390
tail_event_cells: 327
zero_tail_exposed_cells: 0
exact_counter_records: 0
derived_exact_range_records: 0
unknown_exposure_records: 390
proof_eligible_exposure: false
```

The historical artifacts did not contain either:

- a monotonic integer `hashes_attempted` counter attributed to the exact cell;
  or
- a proven completed-range cardinality with known traversal, completion,
  overlap, replay, profile, side, and window semantics.

A18.22 therefore refused to substitute assigned work, elapsed time, nominal
HPS, accepted shares, or dashboard values for exact exposure.

This is a valid negative result:

```text
The tails are observable.
The coordinates are observable.
Exact historical coordinate exposure is not observable.
Therefore the rate-proof gate remains closed.
```

### A18.23 — Exact Exposure Shadow Emitter

A18.23 is the next planned layer. Its purpose is to emit a disabled-by-default,
shadow-only monotonic integer `hashes_attempted` delta after each proven
completed hash batch, bound to a frozen coordinate key and sealed window.

Until that instrument exists and survives offline validation, A18.21 and A18.22
must continue to refuse an exposure-normalized advantage claim.

## Why This Is A Real Proof Discipline

The important achievement is not that JANUS found a pattern. It is that the
system rejected its own attractive interpretation when the denominator was
missing.

```text
A beautiful heatmap is not proof.
One rare tail is not proof.
Repeated overlapping windows are not independent proof.
Assigned work is not completed work.
Unknown is not zero.
A valid ledger is not a valid claim.
```

Proof-of-Observation becomes meaningful precisely where it blocks the observer
from saying more than the evidence permits.

## Public Claim Boundary

Safe public wording:

> JANUS Proof-of-Observation is an observer and evidence-gating method that
> records machine telemetry in an integrity-linked chain, separates facts from
> inference, requires exact exposure and independent holdouts for rate claims,
> and fails closed when the evidence is incomplete.

Do not describe it as:

- proof of machine consciousness;
- distributed consensus;
- a SHA-256 break;
- nonce prediction;
- a mining-profit claim;
- proof that a visual cluster is a causal advantage;
- proof that hash outputs contain deterministic geometric paths.

## Canonical Phrases

```text
Do not trust an impression. Trust the chain of observations.
```

```text
Do not predict the hash. Test whether the tails preserve conditional structure.
```

```text
Hash-chain integrity protects history from silent rewriting.
Claim gates protect understanding from self-deception.
```

```text
We did not lose the proof.
We proved that the available data was insufficient for the proof.
```

## Machine-Readable Record

The companion file
[`proof-of-observation-origin-record.json`](proof-of-observation-origin-record.json)
contains the canonical name, date, definition, lineage, safety boundary, and
claim status in a machine-readable form.
