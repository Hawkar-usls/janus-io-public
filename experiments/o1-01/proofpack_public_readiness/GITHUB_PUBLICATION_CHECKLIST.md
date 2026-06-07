# GitHub Publication Checklist

## Do Not Publish

- Private keys.
- Pool credentials or passwords.
- Private account metadata beyond intentionally public experiment identifiers.
- Large raw logs unless intentionally curated.
- Live dashboard/session/memory files from an active run.
- Proof files before privacy review.
- Anything implying SHA-256 is broken.
- Anything implying guaranteed mining profit.

## Required Before Public Preview

- README draft reviewed.
- Methodology reviewed.
- Wire invariants documented.
- Accepted proof format documented.
- Offline verifier added and tested.
- Benchmark plan included.
- V31 IO evidence summarized:
  - 10000+ clean proofs.
  - z36 accepted proof.
  - reject rate below 0.3 percent around milestone.
  - `wire_change_required=false`.
- Public examples use copied artifacts, not live-state files.

## Readiness Levels

Not yet:
Documentation incomplete or verifier missing.

Internal release:
Docs exist and evidence is organized, but examples are not privacy-reviewed.

Public preview:
Docs are reviewed, verifier exists, and sample copied proofs are safe to publish.

Public claim-ready:
Repeated A/B evidence supports any scheduler advantage claim with conservative language.
