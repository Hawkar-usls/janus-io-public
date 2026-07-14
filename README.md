# JANUS I0

JANUS I0 is an experimental Proof-of-Work measurement and scheduler-research
project. It studies the computation around SHA-256 — work admission, nonce and
lane traversal, exact exposure, rare-tail telemetry, shutdown behavior, stale
work, and evidence quality — while treating SHA-256 itself as intact.

The project is built around a strict rule:

```text
Do not promote an interesting observation into a claim
until provenance, exposure, controls, and independent confirmation exist.
```

## What JANUS does today

The current research toolchain can:

- verify the identity of approved runtime components with SHA-256 digests before
  execution;
- apply deterministic, manifest-bound instrumentation while asserting that
  nonce traversal, hashing, verification, wire, and submit semantics remain
  unchanged;
- collect exact completed-batch exposure and reconcile checked work against
  committed work;
- write normalized JSON/JSONL evidence with linked event hashes so silent edits
  after commitment are detectable;
- separate sealed-window work from post-target overflow and preserve both;
- validate rare-tail metadata, including cardinality and monotonic tail buckets;
- record runtime health, reconnects, stale events, process exit classification,
  and available hashrate measurements;
- fail closed when provenance, exact exposure, ledger integrity, or required
  metadata is incomplete;
- scan public outputs for common credentials, private paths, endpoints, private
  keys, and operational identifiers;
- export compact, machine-readable reports for independent review.

These are measurement and auditability capabilities. They do **not** establish a
cryptographic shortcut, mining advantage, profitability, or source-telemetry
truth.

See [Current engineering capabilities](docs/current-engineering-capabilities.md)
for a precise capability and limitation matrix.

## Current public research status

The latest curated A18 results are intentionally mixed rather than promotional:

| Study | Result | Meaning |
|---|---|---|
| A18.35 Cycle 1 | closed negative | The preregistered candidate did not survive challenge. |
| A18.35 Cycle 2 | no candidate engine executed | Data were collected, but no hypothesis was actually evaluated or exported. |
| A18.36 | inconclusive artifact study | Post-emitter evidence was insufficient for a broader no-artifact claim. |
| A18.37 | measurable post-target overflow | Eight valid windows recorded 8,194,253 post-target hashes, about 1.44% of measured work. Utility and energy remained unknown. |
| A18.38 V3 | no meaningful overflow reduction | Twelve valid randomized windows showed that the tested target-aware quiesce controller did not produce a reliable reduction. |

Negative and inconclusive outcomes are retained because they define the real
engineering boundary and prevent attractive but unsupported conclusions.

Read [A18 status, 2026-07-14](docs/a18-status-2026-07-14.md).

## What JANUS is not

JANUS does not claim that:

- SHA-256 is broken or predictable;
- winning nonces can be inferred;
- a rare accepted share is equivalent to a Bitcoin block;
- a hash chain proves that the original telemetry was true;
- post-target experimental work is automatically useless to a pool;
- the current software is a production mining platform;
- the project has no prior art or direct analogues without a separate review;
- energy savings exist when clean power telemetry was unavailable.

A linked ledger provides **tamper evidence after commitment**. Source identity,
clock correctness, collection completeness, statistical independence, and causal
interpretation require separate controls.

## Proof-of-Observation

JANUS Proof-of-Observation is the project's evidence-gating discipline:

1. preserve facts and their provenance;
2. calculate derived metrics deterministically;
3. keep missing values unknown rather than converting them to zero;
4. link committed observer records for integrity;
5. compare only compatible windows and exact exposure;
6. separate discovery from challenge and replication;
7. emit claims only when predefined gates pass.

Canonical record:

- [Proof-of-Observation](docs/proof-of-observation.md)
- [Machine-readable origin record](docs/proof-of-observation-origin-record.json)

## Repository map

```text
docs/         methodology, claim boundaries, curated research status
scripts/      offline analyzers, scrubbers, and reviewer utilities
src/          importable historical supervisor snapshot
experiments/  curated public summaries and safe proof packs
```

Raw live logs, credentials, local paths, pool identities, unsanitized proof
archives, and private operational state do not belong in the public repository.
Historical single-file runners may remain for lineage, but they are not the
recommended reviewer entry point.

## Reviewer path

For a fast review:

```text
2 minutes   README.md
5 minutes   docs/current-engineering-capabilities.md
10 minutes  docs/a18-status-2026-07-14.md
20 minutes  docs/proof-of-observation.md + docs/evidence-pack-spec.md
30 minutes  docs/reviewer-guide.md + a curated proof pack
```

The desired conclusion is not “trust the author.” It is:

```text
The method, controls, evidence boundary, and unresolved uncertainties
are explicit enough to inspect.
```

## Public-safe quickstart

Repository review and offline analysis only:

```powershell
python scripts\scrub_secrets.py --limit 80
python scripts\analyze_o1.py
python src\janus_io_o1_agent_supervisor_single_fixed.py --help
```

Do not start a real-pool run while preparing, scrubbing, or publishing repository
artifacts.

## Assessment of the architecture

Several strong engineering claims about the current collector architecture are
supported by the code and frozen reports:

- runtime component hash verification exists;
- deterministic instrumentation contracts exist;
- exact-exposure reconciliation exists;
- linked evidence ledgers and validators exist;
- fail-closed decisions and privacy scanning exist;
- PowerShell orchestration and Python supervision have distinct responsibilities.

Stronger descriptions such as “production-ready,” “forensic proof,” “industry
standard,” “no direct analogues,” or a numerical seniority score are opinions,
not established project results. The accurate description is narrower:

> JANUS is an unusually evidence-focused experimental PoW telemetry and scheduler
> research system with reproducibility, integrity, and claim-discipline controls.

## Safety and publication policy

- Keep mining wire, proof verification, and approved hashing semantics frozen in
  observer studies unless a separate change is explicitly authorized.
- Publish negative results and technical nonpasses alongside positive signals.
- Never publish credentials, wallet-like labels, private endpoints, raw private
  paths, or unsanitized live evidence.
- Treat exploratory number-class, glyph, coordinate, or tail patterns as
  hypotheses until preregistered controls and independent confirmation exist.

See [Security and disclosure](SECURITY.md) and
[Contributing](CONTRIBUTING.md).

## License

Apache License 2.0. See [LICENSE](LICENSE).
